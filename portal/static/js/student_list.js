// CSRF token helper from cookie (Django default)
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
const csrftoken = getCookie("csrftoken");

// Navigation button handlers
function goHome() {
  alert("Going to home page...");
  // Replace with actual navigation, e.g. window.location.href = '/home';
}

// Logout confirmation
function confirmLogout(event) {
  if (!confirm("Are you sure you want to logout?")) {
    event.preventDefault();
    return false;
  }
  return true;
}

// Students data array and editing state
let students = [];
let editingId = null;

const tableBody = document.getElementById("studentsTable");
const modalOverlay = document.getElementById("modalOverlay");
const form = document.getElementById("studentForm");
const inputName = document.getElementById("studentName");
const inputSubject = document.getElementById("studentSubject");
const inputMark = document.getElementById("studentMark");
const modalTitle = document.querySelector(".modal-title");
const submitBtn = document.querySelector(".btn-submit");

// Fetch students from backend and render
function loadStudents() {
  fetch("/api/students/")
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        students = data.students;
        renderTable();
      } else {
        alert("Failed to load students: " + data.message);
      }
    })
    .catch(() => alert("Error fetching students from server."));
}

// Render table rows
function renderTable() {
  tableBody.innerHTML = "";

  if (students.length === 0) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td colspan="4" style="text-align:center; padding: 1.5rem; color: #666; font-style: italic;">
        No records found.
      </td>
    `;
    tableBody.appendChild(tr);
    return;
  }

  students.forEach((student) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${student.name}</td>
      <td>${student.subject}</td>
      <td>${student.mark}</td>
      <td>
        <div class="action-dropdown">
          <button class="action-toggle-btn" onclick="toggleDropdown(this)">
              <i class="fa-solid fa-caret-right"></i>
          </button>

          <div class="dropdown-menu">
            <div class="dropdown-item" onclick="editStudent(${student.id})">
              <i class="fa-solid fa-pen-to-square"></i> 
            </div>
            <div class="dropdown-item" onclick="deleteStudent(${student.id})">
              <i class="fa-solid fa-trash"></i>
            </div>
          </div>
        </div>
      </td>
    `;
    tableBody.appendChild(tr);
  });
}


// Open modal for add mode
function openModal() {
  modalOverlay.classList.add("active");
  document.body.style.overflow = "hidden";
  editingId = null;
  modalTitle.innerHTML = '<i class="fa-solid fa-user-plus"></i> Add New Student';
  submitBtn.textContent = "Add Student";
  form.reset();
}

// Close modal
function closeModal(event) {
  if (event && event.target !== event.currentTarget) return;
  modalOverlay.classList.remove("active");
  document.body.style.overflow = "auto";
  closeAllDropdowns();
}

// Submit handler for add/update
function addOrUpdateStudent(event) {
  event.preventDefault();
  const name = inputName.value.trim();
  const subject = inputSubject.value.trim();
  const mark = Number(inputMark.value);

  if (!name || !subject || isNaN(mark) || mark < 0 || mark > 100) {
    alert("Please enter valid data.");
    return;
  }

  if (editingId === null) {
    // Add new
    fetch("/api/add/", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-CSRFToken": csrftoken,
      },
      body: new URLSearchParams({ name, subject, marks: mark }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          students.push(data.student);
          renderTable();
          showNotification("Student added successfully!");
          closeModal();
        } else {
          alert("Add failed: " + data.message);
        }
      })
      .catch(() => alert("Error adding student."));
  } else {
    // Update existing
    fetch(`/students/edit/${editingId}/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-CSRFToken": csrftoken,
      },
      body: new URLSearchParams({ name, subject, marks: mark }),
    })
      .then((res) => {
        if (res.redirected) {
          loadStudents();
          showNotification("Student updated successfully!");
          closeModal();
        } else {
          return res.text().then((text) => {
            alert("Update failed: " + text);
          });
        }
      })
      .catch(() => alert("Error updating student."));
  }
}

// Edit student - fill form and open modal
function editStudent(id) {
  const student = students.find((s) => s.id === id);
  if (!student) return;
  editingId = id;
  inputName.value = student.name;
  inputSubject.value = student.subject;
  inputMark.value = student.mark;
  modalTitle.innerHTML = '<i class="fa-solid fa-pen-to-square"></i> Edit Student';
  submitBtn.textContent = "Update Student";
  modalOverlay.classList.add("active");
  document.body.style.overflow = "hidden";
  closeAllDropdowns();
}

// Delete student with confirmation
function deleteStudent(id) {
  if (confirm("Are you sure you want to delete this student?")) {
    fetch(`/api/delete/${id}/`, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrftoken,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          students = students.filter((s) => s.id !== id);
          renderTable();
          closeAllDropdowns();
          showNotification("Student deleted successfully!");
        } else {
          alert("Delete failed: " + data.message);
        }
      })
      .catch(() => alert("Error deleting student."));
  }
}

// Dropdown toggle & close helpers
function toggleDropdown(button) {
  const dropdown = button.nextElementSibling;
  const icon = button.querySelector("i");
  const isOpen = dropdown.classList.contains("active");

  closeAllDropdowns();

  if (!isOpen) {
    // Open this dropdown only if it was previously closed
    dropdown.classList.add("active");
    icon.classList.remove("fa-caret-right");
    icon.classList.add("fa-caret-down");
  } else {
    // It was open, now closed by closeAllDropdowns, so reset icon
    icon.classList.remove("fa-caret-down");
    icon.classList.add("fa-caret-right");
  }
}

function closeAllDropdowns() {
  document.querySelectorAll(".dropdown-menu.active").forEach((menu) => {
    menu.classList.remove("active");
  });
  // Reset all toggle icons to right arrow
  document.querySelectorAll(".action-toggle-btn i").forEach((icon) => {
    icon.classList.remove("fa-caret-down");
    icon.classList.add("fa-caret-right");
  });
}

document.addEventListener("click", (e) => {
  if (!e.target.closest(".action-dropdown")) {
    closeAllDropdowns();
  }
});

// Simple notification
function showNotification(message) {
  alert(message);
}

// Initial load
loadStudents();
