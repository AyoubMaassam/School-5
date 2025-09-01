from django.urls import path
from . import views

urlpatterns = [
    # Main pages
    path('', views.home, name='home'),
    
    # Student routes
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/search/', views.search_student, name='search_student'),
    path('students/<int:student_id>/', views.student_detail, name='student_detail'),
    path('students/<int:student_id>/edit/', views.edit_student, name='edit_student'),
    path('students/<int:student_id>/delete/', views.delete_student, name='delete_student'),
    path('students/<int:student_id>/enroll/', views.enroll_student_in_groups, name='enroll_student_in_groups'),
    path('students/<int:student_id>/attendance/<int:attendance_id>/excuse/', views.mark_absence_excused, name='mark_absence_excused'),
    path('students/<int:student_id>/print_registration_confirmation/', views.print_registration_fee_confirmation, name='print_registration_confirmation'),
    path('students/<int:student_id>/monthly_payment/', views.student_monthly_payment_view, name='student_monthly_payment'),
    path('students/<int:student_id>/group/<int:group_id>/print_receipt/', views.print_student_payment_receipt, name='print_student_payment_receipt'),
    path('students/<int:student_id>/print_qr_code/', views.print_student_qr_code, name='print_student_qr_code'),
    
    # Teacher routes
    path('teachers/', views.teacher_list, name='teacher_list'),
    path('teachers/add/', views.add_teacher, name='add_teacher'),
    path('teachers/<int:teacher_id>/edit/', views.edit_teacher, name='edit_teacher'),
    path('teachers/<int:teacher_id>/delete/', views.delete_teacher, name='delete_teacher'),
    path('teachers/<int:teacher_id>/financial_detail/', views.teacher_financial_detail, name='teacher_financial_detail'),
    path('teachers/<int:teacher_id>/monthly_payment/', views.teacher_monthly_payment_view, name='teacher_monthly_payment'),
    path('teachers/<int:teacher_id>/group/<int:group_id>/print_receipt/', views.print_teacher_payment_receipt, name='print_teacher_payment_receipt'),
    
    # Group routes
    path('groups/', views.group_list, name='group_list'),
    path('groups/add/', views.add_group, name='add_group'),
    path('groups/<int:group_id>/', views.group_detail, name='group_detail'),
    path('groups/<int:group_id>/edit/', views.edit_group, name='edit_group'),
    path('groups/<int:group_id>/delete/', views.delete_group, name='delete_group'),
    
    # Session routes
    path('sessions/', views.session_list, name='session_list'),
    path('sessions/add/', views.add_session, name='add_session'),
    path('sessions/<int:session_id>/edit/', views.edit_session, name='edit_session'),
    path('sessions/<int:session_id>/delete/', views.delete_session, name='delete_session'),
    path('sessions/<int:session_id>/manage_attendance/', views.manage_session_attendance, name='manage_session_attendance'),
    path('sessions/<int:session_id>/attendance_detail/', views.session_attendance_detail, name='session_attendance_detail'),
    
    # Attendance routes
    path('attendance/', views.attendance_register, name='attendance_register'),
    path('attendance/record/', views.attendance_record, name='attendance_record'),
    
    # Payment routes
    path('payments/student/<int:student_id>/', views.student_payment, name='student_payment'),
    path('payments/teacher/<int:teacher_id>/', views.teacher_payment, name='teacher_payment'),
    path('payments/report/', views.payment_report, name='payment_report'),
    path('financial-reports/logs/', views.action_log_list, name='action_log_list'),
    
    # API endpoints for frontend
    path('api/academic-levels/', views.api_academic_levels, name='api_academic_levels'),
    path('api/subjects/', views.api_subjects, name='api_subjects'),
    path('api/teachers/', views.api_teachers, name='api_teachers'),
    path('api/students/', views.api_students, name='api_students'),
    path('api/groups/', views.api_groups, name='api_groups'),
    path('api/sessions/', views.api_sessions, name='api_sessions'),
    path('api/attendance/record/', views.api_record_attendance, name='api_record_attendance'),
    path('api/attendance/record_by_student/', views.api_record_attendance_by_student, name='api_record_attendance_by_student'),
    path('api/attendance/record_bulk/', views.api_record_bulk_attendance, name='api_record_bulk_attendance'),
    path('api/session/<int:session_id>/attendance/', views.api_get_session_attendance, name='api_get_session_attendance'),
    path('api/group/<int:group_id>/students/', views.api_get_group_students, name='api_get_group_students'),
    path('api/attendance/cancel/', views.api_cancel_attendance, name='api_cancel_attendance'),
    path('api/session/<int:session_id>/mark_all_absent/', views.api_mark_all_absent, name='api_mark_all_absent'),
]