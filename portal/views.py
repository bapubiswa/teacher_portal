
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods, require_GET
from django.utils import timezone
from django.forms import ModelForm
from django.contrib import messages
from .models import Teacher, Student, AuditLog
from .helpers import hash_password, calculate_new_marks
import secrets

# ------------------------------------------------------------------
# In-memory session store (Dictionary-based for this implementation)
# Keys: session tokens, Values: teacher IDs
# ------------------------------------------------------------------
SESSION_STORE = {}

# ==============================
# Authentication Views
# ==============================

def signup_view(request):
    """
    Handles teacher account creation.
    - Validates required fields.
    - Checks for duplicate usernames.
    - Hashes password with salt before storing.
    """
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        if not username or not password:
            return render(request, "portal/signup.html", {"error": "All fields required"})

        if Teacher.objects.filter(username=username).exists():
            return render(request, "portal/signup.html", {"error": "Username already taken"})

        hashed, salt = hash_password(password)
        Teacher.objects.create(
            username=username,
            password_hash=hashed,
            salt=salt,
            created_at=timezone.now()
        )

        messages.success(request, "User created successfully!")
        return redirect("login")

    return render(request, "portal/signup.html")


def forgot_password_view(request):
    """
    Handles teacher password reset without standard Django auth.
    - Step 1: User enters username; system validates existence.
    - Step 2: If username exists, display new password fields.
    - Step 3: Validate and update hashed password with new salt.
    """
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        # Step 1: Username check only
        if username and not new_password and not confirm_password:
            if not Teacher.objects.filter(username=username).exists():
                return render(request, "portal/forgot_password.html", {
                    "error": "Username not found"
                })
            return render(request, "portal/forgot_password.html", {
                "username": username,
                "show_password_fields": True
            })

        # Step 2: Password reset
        if username and new_password and confirm_password:
            if not Teacher.objects.filter(username=username).exists():
                return render(request, "portal/forgot_password.html", {
                    "error": "Username not found"
                })

            if new_password != confirm_password:
                return render(request, "portal/forgot_password.html", {
                    "username": username,
                    "show_password_fields": True,
                    "error": "Passwords do not match"
                })

            teacher = Teacher.objects.get(username=username)
            hashed, salt = hash_password(new_password)
            teacher.password_hash = hashed
            teacher.salt = salt
            teacher.save()

            # Success response to trigger frontend alert + redirect
            return render(request, "portal/forgot_password.html", {
                "success": True
            })

        return render(request, "portal/forgot_password.html", {
            "error": "Please fill all required fields"
        })

    return render(request, "portal/forgot_password.html")


def login_view(request):
    """
    Custom teacher login with in-memory session handling.
    - Hashes input password with stored salt.
    - Compares hash with stored password hash.
    - On success, issues random session token stored in SESSION_STORE.
    - Sets HttpOnly, SameSite=Lax cookie for session management.
    """
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        try:
            teacher = Teacher.objects.get(username=username)
        except Teacher.DoesNotExist:
            return render(request, "portal/login.html", {"error": "Invalid credentials"})

        hashed, _ = hash_password(password, teacher.salt)
        if hashed == teacher.password_hash:
            token = secrets.token_hex(16)  # Secure random token
            SESSION_STORE[token] = teacher.id
            resp = redirect("students_list")
            resp.set_cookie("session_token", token, httponly=True, samesite="Lax")
            return resp

        return render(request, "portal/login.html", {"error": "Invalid credentials"})

    return render(request, "portal/login.html")


def logout_view(request):
    """
    Ends the teacher's session by:
    - Removing token from SESSION_STORE.
    - Deleting the session cookie.
    """
    token = request.COOKIES.get("session_token")
    if token in SESSION_STORE:
        del SESSION_STORE[token]
    resp = redirect("login")
    resp.delete_cookie("session_token")
    return resp


def _get_current_teacher(request):
    """
    Helper to fetch currently logged-in teacher from in-memory session.
    Returns:
        Teacher object if valid session, else None.
    """
    token = request.COOKIES.get("session_token")
    if not token or token not in SESSION_STORE:
        return None
    try:
        return Teacher.objects.get(id=SESSION_STORE[token])
    except Teacher.DoesNotExist:
        return None


# ==============================
# Student Management
# ==============================

def students_list(request):
    """
    Renders the main student list page for authenticated teachers.
    Data is fetched asynchronously via AJAX from get_students().
    """
    teacher = _get_current_teacher(request)
    if not teacher:
        return redirect("login")

    return render(request, "portal/students_list.html", {"username": teacher.username})


@require_GET
def get_students(request):
    """
    API endpoint: Returns all students as JSON.
    Access restricted to authenticated teachers.
    """
    teacher = _get_current_teacher(request)
    if not teacher:
        return JsonResponse({"success": False, "message": "Not authenticated"}, status=401)

    students = Student.objects.all().order_by("id")
    students_list = [
        {"id": s.id, "name": s.name, "subject": s.subject, "mark": s.marks}
        for s in students
    ]
    return JsonResponse({"success": True, "students": students_list})


@require_POST
def add_student(request):
    """
    Adds a new student OR updates marks for existing name+subject.
    - Rejects duplicate name+subject+marks.
    - If same name+subject exists, updates marks via calculate_new_marks().
    - Enforces max total marks <= 100.
    - Logs all changes to AuditLog for traceability.
    """
    teacher = _get_current_teacher(request)
    if not teacher:
        return JsonResponse({"success": False, "message": "Not authenticated"}, status=401)

    name = request.POST.get("name", "").strip()
    subject = request.POST.get("subject", "").strip()

    try:
        marks = int(request.POST.get("marks", "0"))
    except ValueError:
        return JsonResponse({"success": False, "message": "Marks must be a number"}, status=400)

    if not name or not subject:
        return JsonResponse({"success": False, "message": "All fields are required"}, status=400)
    if marks < 0 or marks > 100:
        return JsonResponse({"success": False, "message": "Marks must be between 0 and 100"}, status=400)

    # Case 1: Exact same record already exists
    existing = Student.objects.filter(name=name, subject=subject, marks=marks).first()
    if existing:
        return JsonResponse({
            "success": False,
            "message": "Student with same name, subject and marks already exists"
        }, status=400)

    # Case 2: Same student & subject exists, marks different -> update
    student = Student.objects.filter(name=name, subject=subject).first()
    if student:
        new_marks = calculate_new_marks(student.marks, marks)
        if new_marks > 100:
            return JsonResponse({"success": False, "message": "Total marks cannot exceed 100"}, status=400)

        old_marks = student.marks
        student.marks = new_marks
        student.updated_at = timezone.now()
        student.save()

        AuditLog.objects.create(
            teacher_id=teacher.id,
            student_id=student.id,
            action="update",
            old_marks=old_marks,
            new_marks=new_marks,
            timestamp=timezone.now()
        )

        return JsonResponse({
            "success": True,
            "student": {
                "id": student.id,
                "name": student.name,
                "subject": student.subject,
                "mark": student.marks
            }
        })

    # Case 3: Completely new student -> insert
    student = Student.objects.create(
        name=name,
        subject=subject,
        marks=marks,
        created_at=timezone.now(),
        updated_at=timezone.now()
    )

    AuditLog.objects.create(
        teacher_id=teacher.id,
        student_id=student.id,
        action="create",
        old_marks=None,
        new_marks=marks,
        timestamp=timezone.now()
    )

    return JsonResponse({
        "success": True,
        "student": {
            "id": student.id,
            "name": student.name,
            "subject": student.subject,
            "mark": student.marks
        }
    })


class StudentForm(ModelForm):
    """Django ModelForm for editing Student entries."""
    class Meta:
        model = Student
        fields = ['name', 'subject', 'marks']


@require_http_methods(["GET", "POST"])
def edit_student_form(request, student_id):
    """
    Handles inline student editing via a form.
    - GET: Render form with existing data.
    - POST: Validate and update student data.
    - Logs changes to AuditLog.
    """
    teacher = _get_current_teacher(request)
    if not teacher:
        return redirect('login')

    student = get_object_or_404(Student, id=student_id)

    if request.method == "POST":
        old_marks = student.marks

        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            updated_student = form.save(commit=False)
            updated_student.updated_at = timezone.now()
            updated_student.save()

            AuditLog.objects.create(
                teacher_id=teacher.id,
                student_id=updated_student.id,
                action="edit",
                old_marks=old_marks,
                new_marks=updated_student.marks,
                timestamp=timezone.now()
            )
            return redirect('students_list')
        else:
            return render(request, 'portal/edit_student_form.html', {'form': form, 'student': student})

    form = StudentForm(instance=student)
    return render(request, 'portal/edit_student_form.html', {'form': form, 'student': student})


@require_POST
def delete_student(request, student_id):
    """
    Deletes a student record.
    - Validates authentication.
    - Logs deletion to AuditLog with old marks preserved.
    """
    teacher = _get_current_teacher(request)
    if not teacher:
        return JsonResponse({"success": False, "message": "Not authenticated"}, status=401)

    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return JsonResponse({"success": False, "message": "Student not found"}, status=404)

    old_marks = student.marks
    sid = student.id

    AuditLog.objects.create(
        teacher_id=teacher.id,
        student_id=sid,
        action="delete",
        old_marks=old_marks,
        new_marks=None,
        timestamp=timezone.now()
    )

    student.delete()
    return JsonResponse({"success": True, "student_id": sid})
