// Main JavaScript file for Maasam School Management System

// DOM elements
const sidebarToggle = document.getElementById('sidebar-toggle');
const sidebar = document.querySelector('.sidebar');
const backToHome = document.querySelector('.back-to-home');

// Toggle sidebar on mobile
if (sidebarToggle) {
  sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
  });
}

// Back to home button
if (backToHome) {
  backToHome.addEventListener('click', () => {
    window.location.href = '/';
  });
}

// Dropdown handlers
document.addEventListener('DOMContentLoaded', () => {
  // Note: "DOM Content Loaded: Setting up group form handler." was removed from here
  // as handleGroupForm itself will log its execution.
  // Handle academic level dropdowns
  const academicLevelDropdowns = document.querySelectorAll('.academic-level-dropdown');
  if (academicLevelDropdowns.length > 0) {
    fetchAcademicLevels().then(levels => {
      if (levels && levels.length > 0) {
        academicLevelDropdowns.forEach(dropdown => {
          populateAcademicLevelDropdown(dropdown, levels);
        });
      } else {
        showAlert('لم يتم العثور على مستويات دراسية.', 'warning');
        academicLevelDropdowns.forEach(dropdown => { clearDropdown(dropdown, 'لا توجد مستويات حالياً'); }); // Clear dropdowns if no levels
      }
    }).catch(error => {
      showAlert('حدث خطأ أثناء معالجة قائمة المستويات الدراسية: ' + error.message, 'error');
    });
  }

  // Handle subject dropdowns
  const subjectDropdowns = document.querySelectorAll('.subject-dropdown');
  if (subjectDropdowns.length > 0) {
    fetchSubjects().then(subjects => {
      subjectDropdowns.forEach(dropdown => {
        populateSubjectDropdown(dropdown, subjects);
      });
    });
  }

  // Handle teacher dropdowns (dependent on subject)
  const subjectDropdownForTeacher = document.querySelector('.subject-dropdown-for-teacher');
  const teacherDropdown = document.querySelector('.teacher-dropdown');
  if (subjectDropdownForTeacher && teacherDropdown) {
    subjectDropdownForTeacher.addEventListener('change', () => {
      const subjectId = subjectDropdownForTeacher.value;
      if (subjectId) {
        fetchTeachersBySubject(subjectId).then(teachers => {
          populateTeacherDropdown(teacherDropdown, teachers);
        });
      } else {
        clearDropdown(teacherDropdown, 'اختر المدرس');
      }
    });
  }
});

// API functions for data fetching
async function fetchAcademicLevels() {
  try {
    const response = await fetch('/api/academic-levels/');
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    return await response.json();
  } catch (error) {
    return [];
  }
}

async function fetchSubjects() {
  try {
    const response = await fetch('/api/subjects/');
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    return await response.json();
  } catch (error) {
    return [];
  }
}

async function fetchTeachersBySubject(subjectId) {
  try {
    const response = await fetch(`/api/teachers/?subject_id=${subjectId}`);
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    return await response.json();
  } catch (error) {
    return [];
  }
}

async function fetchStudents(query = '') {
  try {
    const url = query ? `/api/students/?q=${encodeURIComponent(query)}` : '/api/students/';
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    return await response.json();
  } catch (error) {
    return [];
  }
}

async function fetchGroups() {
  try {
    const response = await fetch('/api/groups/');
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    return await response.json();
  } catch (error) {
    return [];
  }
}

async function fetchSessionsByGroup(groupId) {
  try {
    const response = await fetch(`/api/sessions/?group_id=${groupId}`);
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    return await response.json();
  } catch (error) {
    return [];
  }
}

// Utility functions for populating dropdowns
function populateAcademicLevelDropdown(dropdown, levels) {
  if (!dropdown) {
    return;
  }
  if (!levels || levels.length === 0) {
    clearDropdown(dropdown, "لا توجد مستويات حالياً");
    return;
  }
  clearDropdown(dropdown, 'اختر المستوى الدراسي'); // This clears the dropdown
  
  // Group levels by category
  const primaryLevels = levels.filter(level => level.category === 'PRIMARY');
  const middleLevels = levels.filter(level => level.category === 'MIDDLE');
  const highLevels = levels.filter(level => level.category === 'HIGH');
  
  // Create option groups
  if (primaryLevels.length > 0) {
    const primaryGroup = document.createElement('optgroup');
    primaryGroup.label = 'الابتدائي';
    primaryLevels.forEach(level => {
      const option = document.createElement('option');
      option.value = level.id;
      option.textContent = level.name;
      primaryGroup.appendChild(option);
    });
    dropdown.appendChild(primaryGroup);
  }
  
  if (middleLevels.length > 0) {
    const middleGroup = document.createElement('optgroup');
    middleGroup.label = 'المتوسط';
    middleLevels.forEach(level => {
      const option = document.createElement('option');
      option.value = level.id;
      option.textContent = level.name;
      middleGroup.appendChild(option);
    });
    dropdown.appendChild(middleGroup);
  }
  
  if (highLevels.length > 0) {
    const highGroup = document.createElement('optgroup');
    highGroup.label = 'الثانوي';
    highLevels.forEach(level => {
      const option = document.createElement('option');
      option.value = level.id;
      option.textContent = level.name;
      highGroup.appendChild(option);
    });
    dropdown.appendChild(highGroup);
  }

  // Dispatch custom event if this is the target dropdown for add_group page
  if (dropdown.id === 'academic-levels') {
    const event = new CustomEvent('academicLevelsPopulated', {
      detail: { dropdownId: dropdown.id }
    });
    dropdown.dispatchEvent(event);
  }
}

function populateSubjectDropdown(dropdown, subjects) {
  clearDropdown(dropdown, 'اختر المادة');
  subjects.forEach(subject => {
    const option = document.createElement('option');
    option.value = subject.id;
    option.textContent = subject.name;
    dropdown.appendChild(option);
  });
}

function populateTeacherDropdown(dropdown, teachers) {
  clearDropdown(dropdown, 'اختر المدرس');
  teachers.forEach(teacher => {
    const option = document.createElement('option');
    option.value = teacher.id;
    option.textContent = teacher.name;
    dropdown.appendChild(option);
  });
}

function clearDropdown(dropdown, placeholderText) {
  dropdown.innerHTML = '';
  // Only add a default placeholder option for non-multi-select or non-academic-levels dropdowns
  if (dropdown.id !== 'academic-levels') {
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = placeholderText;
    dropdown.appendChild(defaultOption);
  }
}

// Form submission handlers
function handleStudentForm() {
  const studentForm = document.getElementById('student-form'); // Assuming this ID
  if (!studentForm) return;
  if (studentForm.hasAttribute('data-student-submit-listener-attached')) {
      console.log('Student form submit listener already attached.');
      return;
  }
  console.log('Attaching submit listener to student form.');
  studentForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Basic form validation
    const firstName = document.getElementById('first-name').value;
    const lastName = document.getElementById('last-name').value;
    const phone = document.getElementById('phone').value;
    const guardianPhone = document.getElementById('guardian-phone').value;
    const birthDay = document.getElementById('birth-day').value;
    const birthMonth = document.getElementById('birth-month').value;
    const birthYear = document.getElementById('birth-year').value;
    const academicLevel = document.getElementById('academic-level').value;
    const regFeePaid = document.getElementById('reg-fee-paid').checked;
    
    if (!firstName || !lastName || !phone || !guardianPhone || !birthDay || !birthMonth || !birthYear || !academicLevel) {
      showAlert('جميع الحقول مطلوبة', 'error');
      return;
    }
    
    // Prepare data to send to Django backend
    const studentData = {
      first_name: firstName,
      last_name: lastName,
      phone_number: phone,
      guardian_phone: guardianPhone,
      birth_day: parseInt(birthDay),
      birth_month: parseInt(birthMonth),
      birth_year: parseInt(birthYear),
      academic_level: academicLevel,
      registration_fee_paid: regFeePaid
    };
    
    // Mock API call (to be replaced with actual backend call)
    try {
      // This would be a real API call in production
      
      // Mock successful response
      setTimeout(() => {
        showAlert('تم تسجيل الطالب بنجاح', 'success');
        // Redirect to enroll student in groups
        window.location.href = `/students/enroll/?student_id=123`;
      }, 1000);
    } catch (error) {
      showAlert('حدث خطأ أثناء تسجيل الطالب', 'error');
    }
  });
  studentForm.setAttribute('data-student-submit-listener-attached', 'true');
}

function handleTeacherForm() {
  const teacherForm = document.getElementById('teacher-form'); // Assuming this ID
  if (!teacherForm) return;
  if (teacherForm.hasAttribute('data-teacher-submit-listener-attached')) {
      console.log('Teacher form submit listener already attached.');
      return;
  }
  console.log('Attaching submit listener to teacher form.');
  teacherForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Basic form validation
    const firstName = document.getElementById('first-name').value;
    const lastName = document.getElementById('last-name').value;
    const phone = document.getElementById('phone').value;
    const subject = document.getElementById('subject').value;
    
    if (!firstName || !lastName || !phone || !subject) {
      showAlert('جميع الحقول مطلوبة', 'error');
      return;
    }
    
    // Prepare data to send to Django backend
    const teacherData = {
      first_name: firstName,
      last_name: lastName,
      phone_number: phone,
      subject: subject
    };
    
    // Mock API call (to be replaced with actual backend call)
    try {
      // This would be a real API call in production
      
      // Mock successful response
      setTimeout(() => {
        showAlert('تم تسجيل المدرس بنجاح', 'success');
        // Redirect to teachers list
        window.location.href = '/teachers/';
      }, 1000);
    } catch (error) {
      showAlert('حدث خطأ أثناء تسجيل المدرس', 'error');
    }
  });
  teacherForm.setAttribute('data-teacher-submit-listener-attached', 'true');
}

function handleGroupForm() {
    const groupForm = document.getElementById('group-form');
    if (!groupForm) {
        // console.log("handleGroupForm: group-form not found. Exiting."); // Optional: for debugging if form isn't always present
        return;
    }

    // Add console log before the attribute check
    console.log('handleGroupForm called. Has attribute data-group-submit-listener-attached:', groupForm.hasAttribute('data-group-submit-listener-attached'));

    // If the form already has our specific handler, don't add it again.
    if (groupForm.hasAttribute('data-group-submit-listener-attached')) {
        return;
    }


    const submitHandler = async (e) => {
        console.log('Submit handler triggered for group form.'); // Log at the start of the handler
        e.preventDefault();

        const submitButton = document.getElementById('create-group-btn');
        if (submitButton) {
            submitButton.disabled = true;
        }

        // Gather form data (ensure all IDs are correct)
        const groupName = document.getElementById('group-name').value;
        const subjectEl = document.getElementById('subject');
        const teacherEl = document.getElementById('teacher');
        const priceEl = document.getElementById('price');
        const dayEl = document.getElementById('session-day');
        const startTimeEl = document.getElementById('start-time');
        const durationEl = document.getElementById('duration');
        const academicLevelsEl = document.getElementById('academic-levels');

        const subject = subjectEl ? subjectEl.value : '';
        const teacher = teacherEl ? teacherEl.value : '';
        const price = priceEl ? priceEl.value : '';
        const day = dayEl ? dayEl.value : '';
        const startTime = startTimeEl ? startTimeEl.value : '';
        const duration = durationEl ? durationEl.value : '';
        const academicLevels = academicLevelsEl ? Array.from(academicLevelsEl.selectedOptions).map(option => option.value) : [];

        // Detailed logging for validation


        if (!groupName || !subject || !teacher || !price || !day || !startTime || !duration || academicLevels.length === 0) {
            showAlert('جميع الحقول مطلوبة', 'error');
            if (submitButton) {
                submitButton.disabled = false;
            }
            return;
        }

        const groupData = {
            name: groupName,
            subject: subject,
            teacher: teacher,
            academic_levels: academicLevels,
            price_per_4_sessions: parseFloat(price),
            session_day: parseInt(day),
            session_start_time: startTime,
            session_duration: parseFloat(duration)
        };

        const csrfToken = getCookie('csrftoken');

        fetch('/groups/add/', {
            method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(groupData)
    })
    .then(async response => {
      if (response.ok) {
        return response.json();
      } else {
        // Try to parse error JSON, then throw an error to be caught
        const errorResult = await response.json().catch(() => ({ error: 'فشل في تحليل استجابة الخطأ من الخادم.' }));
        throw { status: response.status, errorResult: errorResult };
      }
    })
    .then(result => {
      if (result.status === 'success') {
        showAlert(result.message || 'تم إنشاء المجموعة بنجاح!', 'success');
        if (result.redirect_url) {
          window.location.href = result.redirect_url;
        } else {
          window.location.href = '/groups/'; // Fallback redirect
        }
      } else {
        // Handle backend-defined errors (e.g., validation errors)
        showAlert(result.error || 'فشل إنشاء المجموعة.', 'error');
      }
    })
    .catch(errorObj => {
      // Handle network errors or errors thrown from non-ok responses
      if (errorObj && errorObj.errorResult && errorObj.errorResult.error) {
        showAlert(errorObj.errorResult.error, 'error');
      } else if (errorObj && errorObj.status) {
        showAlert(`حدث خطأ في الخادم: ${errorObj.status}`, 'error');
      } else {
        showAlert('حدث خطأ غير متوقع أثناء إنشاء المجموعة.', 'error');
      }
    })
    .finally(() => {
        if (submitButton) {
            submitButton.disabled = false;
        }
    });
  };

  // Remove existing listener before adding, if one was attached by this specific named handler.
  // This is tricky if the handler is anonymous or its reference is lost.
  // The data attribute is a simpler guard if `handleGroupForm` is truly the single point of listener addition.
  console.log('Attaching submit listener to group form.'); // Log before adding the listener
  groupForm.addEventListener('submit', submitHandler);
  groupForm.setAttribute('data-group-submit-listener-attached', 'true'); // Use setAttribute for wider compatibility
}

// Helper function to get CSRF token
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Attendance registration handler
function handleAttendanceRegistration() {
  const recordButton = document.getElementById('record-attendance-btn');
  if (!recordButton) return; // If button isn't there, no listeners to attach
  if (recordButton.hasAttribute('data-attendance-listeners-attached')) {
      console.log('Attendance registration listeners already attached.');
      return;
  }

  const sessionSelect = document.getElementById('session-select');
  const studentSelect = document.getElementById('student-select');
  const scanInput = document.getElementById('scan-input'); // Existing

  if (!sessionSelect || !studentSelect || !scanInput) {
    // If any of the crucial elements for the handler logic are not on the page, do not proceed.
    // console.warn("Attendance registration core elements (selects, input) not found. Skipping handler setup.");
    return;
  }
  console.log('Attaching attendance registration listeners.');
  const processAttendance = () => {
    const sessionId = sessionSelect.value;
    let studentId = scanInput.value.trim();

    if (!sessionId) {
      showAlert('الرجاء اختيار الحصة أولاً.', 'warning');
      document.getElementById('session-select').scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    if (studentId) {
      // If scan input has value, prioritize it.
      // Potentially, this could be a barcode that needs to be mapped to a student ID via another API call
      // For now, assuming scanInput directly provides a student_id or a scannable identifier.
      // If it's a barcode, the backend API /api/attendance/record/ would need to handle it,
      // or a new API endpoint /api/student/lookup-by-barcode/ would be needed.
      // For this implementation, we'll assume scanInput provides the student_id directly.
    } else {
      // If scan input is empty, use the student dropdown.
      studentId = studentSelect.value;
      if (!studentId) {
        showAlert('الرجاء مسح بطاقة الطالب أو اختيار الطالب يدوياً.', 'warning');
        return;
      }
    }

    registerAttendance(sessionId, studentId);
    scanInput.value = ''; // Clear scan input after processing
  };

  recordButton.addEventListener('click', processAttendance);

  scanInput.addEventListener('keyup', (e) => {
    if (e.key === 'Enter') {
      processAttendance();
    }
  });
  recordButton.setAttribute('data-attendance-listeners-attached', 'true');
  console.log('Attached attendance registration listeners.');
}

async function registerAttendance(sessionId, studentId) {
  const apiUrl = '/api/attendance/record/';
  const csrfToken = getCookie('csrftoken');

  try {
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({
        session_id: sessionId,
        student_id: studentId // Assuming studentId is the direct ID. If it's a barcode, backend needs to handle.
      })
    });

    const data = await response.json(); // Attempt to parse JSON regardless of response.ok for error messages

    if (response.ok) {
      if (data.status === 'success' || data.status === 'already_registered') {
        showAlert(data.message, data.status === 'success' ? 'success' : 'info'); // 'already_registered' as info
        if (data.status === 'success') {
          // Construct a record object for addAttendanceToLogTable based on API response
          // const attendanceRecord = {
          //   time: data.attendance_time, // Assuming backend sends 'attendance_time'
          //   student_name: data.student_name,
          //   session_info: data.session_info, // Contains group name, date, time
          //   payment_status_display: data.payment_status // e.g., "Not Paid (Default)"
          // };
          // addAttendanceToLogTable(attendanceRecord); // Replaced by full table refresh below

          // Refresh attendance table and student list
          const sessionSelect = document.getElementById('session-select');
          if (sessionSelect && sessionSelect.value) {
            const currentSessionId = sessionSelect.value;
            const selectedOption = sessionSelect.options[sessionSelect.selectedIndex];
            const groupId = selectedOption ? selectedOption.dataset.groupId : null;

            if (currentSessionId && typeof fetchAndDisplayAttendance === 'function') {
              const updatedPresentIds = await fetchAndDisplayAttendance(currentSessionId);
              if (groupId && typeof fetchAndPopulateGroupStudents === 'function') {
                await fetchAndPopulateGroupStudents(groupId, updatedPresentIds);
              } else if (!groupId) {
                console.warn('Group ID not found for fetchAndPopulateGroupStudents.');
              } else {
                console.warn('fetchAndPopulateGroupStudents is not defined or not a function.');
              }
            } else if (!currentSessionId) {
                console.warn('Session ID not found for fetchAndDisplayAttendance.');
            }
            else {
              console.warn('fetchAndDisplayAttendance is not defined or not a function.');
            }
          } else {
            console.warn('Session select element not found or no session selected.');
          }
        }
      } else {
        // Other backend-defined statuses that are not outright errors but might be warnings
        showAlert(data.message || 'استجابة غير متوقعة من الخادم.', 'warning');
      }
    } else {
      // HTTP error (4xx, 5xx)
      showAlert(data.message || `خطأ في تسجيل الحضور: ${response.status}`, 'error');
    }
  } catch (error) {
    showAlert('حدث خطأ في الشبكة أو مشكلة في الاتصال بالخادم.', 'error');
  }
}

function addAttendanceToLogTable(record) {
  const tbody = document.getElementById('today-attendance-tbody');
  if (!tbody) return;

  const noAttendanceRow = document.getElementById('no-attendance-row');
  if (noAttendanceRow) {
    noAttendanceRow.remove();
  }

  const newRow = tbody.insertRow(0); // Insert at the top

  const timeCell = newRow.insertCell();
  // Format time if needed, assuming record.time is a string like "YYYY-MM-DD HH:MM:SS"
  try {
    const dateObj = new Date(record.time);
    timeCell.textContent = dateObj.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch (e) {
    timeCell.textContent = record.time; // Fallback
  }
  
  const studentCell = newRow.insertCell();
  studentCell.textContent = record.student_name;

  const sessionCell = newRow.insertCell();
  // Extract group name from session_info (e.g., "GroupName - YYYY-MM-DD HH:MM")
  sessionCell.textContent = record.session_info.split(' - ')[0] || record.session_info;


  const paymentCell = newRow.insertCell();
  paymentCell.textContent = record.payment_status_display;
  // You might want to add classes for styling based on payment status
  if (record.payment_status_display.includes("Not Paid")) {
    paymentCell.classList.add('text-danger');
  } else {
    paymentCell.classList.add('text-success');
  }
}

// Remove or comment out showGroupSelectionDialog as it's not used with the new API
/*
function showGroupSelectionDialog(data) {
  const dialogContainer = document.createElement('div');
  dialogContainer.className = 'dialog-overlay';
*/

// The old showAttendanceResult is not needed anymore as showAlert is called directly
// from registerAttendance. If specific formatting for attendance results is needed
// beyond what showAlert provides, this function could be adapted or a new one created.

// Student search
function handleStudentSearch() {
  const searchForm = document.getElementById('student-search-form'); // Assuming this ID
  if (!searchForm) return;
  if (searchForm.hasAttribute('data-search-submit-listener-attached')) {
      console.log('Student search submit listener already attached.');
      return;
  }
  
  const resultsContainer = document.getElementById('search-results');
  if (!resultsContainer) return; // Also ensure results container is present if form is

  console.log('Attaching submit listener to student search form.');
  searchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const searchInput = document.getElementById('search-input').value.trim();
    if (!searchInput) {
      showAlert('يرجى إدخال اسم الطالب أو الرقم المميز', 'warning');
      return;
    }
    
    try {
      const students = await fetchStudents(searchInput);
      displaySearchResults(students, resultsContainer);
    } catch (error) {
      showAlert('حدث خطأ أثناء البحث', 'error');
    }
  });
  searchForm.setAttribute('data-search-submit-listener-attached', 'true');
}

function displaySearchResults(students, container) {
  if (students.length === 0) {
    container.innerHTML = '<p class="text-center">لا توجد نتائج</p>';
    return;
  }
  
  container.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>الاسم</th>
          <th>المستوى الدراسي</th>
          <th>الإجراءات</th>
        </tr>
      </thead>
      <tbody>
        ${students.map(student => `
          <tr>
            <td>${student.name}</td>
            <td>${student.academic_level}</td>
            <td>
              <a href="/students/${student.id}/" class="btn btn-primary btn-sm">عرض</a>
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

// Alert system
function showAlert(message, type = 'info') {
  const alertContainer = document.getElementById('alert-container') || createAlertContainer();

  // Prevent multiple identical alerts
  const existingAlerts = alertContainer.querySelectorAll(`.alert-${type}`);
  for (let existing of existingAlerts) {
    // Check text content excluding the close button (which is a child element)
    if (existing.firstChild && existing.firstChild.nodeType === Node.TEXT_NODE && existing.firstChild.textContent === message) {
      // Optional: Could reset its fade-out timer here if desired
      // For now, just prevent showing a duplicate.
      return;
    }
  }
  
  const alert = document.createElement('div');
  alert.className = `alert alert-${type} slide-in`;
  alert.innerHTML = message;
  
  const closeBtn = document.createElement('button');
  closeBtn.className = 'alert-close';
  closeBtn.innerHTML = '×';
  closeBtn.addEventListener('click', () => {
    alert.classList.add('fade-out');
    setTimeout(() => {
      alertContainer.removeChild(alert);
    }, 300);
  });
  
  alert.appendChild(closeBtn);
  alertContainer.appendChild(alert);
  
  setTimeout(() => {
    alert.classList.add('fade-out');
    setTimeout(() => {
      if (alertContainer.contains(alert)) {
        alertContainer.removeChild(alert);
      }
    }, 300);
  }, 5000);
}

function createAlertContainer() {
  const container = document.createElement('div');
  container.id = 'alert-container';
  document.body.appendChild(container);
  return container;
}

// Initialize forms when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  handleStudentForm();
  handleTeacherForm();
  handleGroupForm();
  handleAttendanceRegistration();
  handleStudentSearch();
  applyInitialTheme(); // Apply theme on load

  const themeToggleButton = document.getElementById('theme-toggle-btn');
  if (themeToggleButton) {
    themeToggleButton.addEventListener('click', toggleTheme);
  }

  const academicLevelsSelect = document.getElementById('academic-levels');
  if (academicLevelsSelect && typeof Choices !== 'undefined') {
    academicLevelsSelect.addEventListener('academicLevelsPopulated', function(event) {
      if (event.target.getAttribute('data-choices-initialized')) {
          return;
      }

      new Choices(event.target, {
        placeholderValue: 'المستويات الدراسية المتوافقة',
        removeItemButton: true,
        searchPlaceholderValue: 'ابحث...',
      });
      event.target.setAttribute('data-choices-initialized', 'true');
    });
  }
});

// Theme Management
const THEME_KEY = 'user-theme-preference';

function applyInitialTheme() {
  const savedTheme = localStorage.getItem(THEME_KEY);
  const themeToggleButton = document.getElementById('theme-toggle-btn');
  const sunIcon = document.getElementById('theme-icon-sun');
  const moonIcon = document.getElementById('theme-icon-moon');

  if (savedTheme === 'dark') {
    document.body.classList.add('dark-mode');
    if (themeToggleButton && sunIcon && moonIcon) {
        sunIcon.style.display = 'none';
        moonIcon.style.display = 'inline-block';
    }
  } else {
    document.body.classList.remove('dark-mode'); // Default to light
    if (themeToggleButton && sunIcon && moonIcon) {
        sunIcon.style.display = 'inline-block';
        moonIcon.style.display = 'none';
    }
  }
}

function toggleTheme() {
  document.body.classList.toggle('dark-mode');
  const isDarkMode = document.body.classList.contains('dark-mode');
  localStorage.setItem(THEME_KEY, isDarkMode ? 'dark' : 'light');

  const themeToggleButton = document.getElementById('theme-toggle-btn');
  const sunIcon = document.getElementById('theme-icon-sun');
  const moonIcon = document.getElementById('theme-icon-moon');

  if (themeToggleButton && sunIcon && moonIcon) {
    if (isDarkMode) {
        sunIcon.style.display = 'none';
        moonIcon.style.display = 'inline-block';
    } else {
        sunIcon.style.display = 'inline-block';
        moonIcon.style.display = 'none';
    }
  }
}