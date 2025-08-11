
from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('register/', views.signup_view, name='register'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('students/', views.students_list, name='students_list'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),

    # API endpoints for AJAX
    path('api/students/', views.get_students, name='get_students'),
    path('api/add/', views.add_student, name='add_student'),
    path('students/edit/<int:student_id>/', views.edit_student_form, name='edit_student_form'),
    path('api/delete/<int:student_id>/', views.delete_student, name='delete_student'),
]
