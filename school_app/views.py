from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseRedirect, Http404
from django.db import transaction # For atomic operations if needed, though simple creation might not strictly need it yet
from decimal import Decimal # Ensure Decimal is imported
from .models import Student, Teacher, AcademicLevel, Subject, Group, Session, Attendance, ActionLog, StudentGroup
from django.urls import reverse # For redirecting with arguments
import datetime # For year validation
import math # For floor function
from django.db.models import Q, Sum # For complex queries
from django.db import IntegrityError # For catching unique constraint violations
from django.contrib import messages # For success/error messages
from django.utils import timezone # Moved to top
from datetime import timedelta # Ensure timedelta is imported
from django.urls import reverse_lazy
from .forms import GroupForm, SessionForm # Import GroupForm and SessionForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.csrf import csrf_exempt
import logging

# Helper function for logging
logger = logging.getLogger(__name__)
def log_action(action_type, object_name, details=""): # details is now optional
    try:
        ActionLog.objects.create(
            action_type=action_type,
            object_name=object_name,
            details=details
        )
    except Exception as e:
        # Handle potential errors during logging, e.g., print to server log
        logger.error(f"Error logging action '{action_type}' for '{object_name}': {e}")

# Main pages
def home(request):
    students_count = Student.objects.count()
    teachers_count = Teacher.objects.count()
    groups_count = Group.objects.count()

    today = timezone.now().date()
    now_time = timezone.now().time()

    sessions_today_qs = Session.objects.filter(date=today).select_related('group', 'group__subject', 'group__teacher').order_by('start_time')

    upcoming_or_ongoing_sessions_today = []
    for session in sessions_today_qs:
        # Combine session's start_time with today's date to create a datetime object
        # Ensure this datetime is timezone-aware if comparing with timezone.now()
        # If session.start_time is naive, make it aware based on project's timezone settings
        start_datetime_naive = datetime.datetime.combine(today, session.start_time)
        start_datetime_aware = timezone.make_aware(start_datetime_naive) # Make it timezone-aware

        # Calculate end datetime
        end_datetime_aware = start_datetime_aware + datetime.timedelta(hours=float(session.duration))
        session_end_time_aware = end_datetime_aware.time()

        if session_end_time_aware > now_time:
            upcoming_or_ongoing_sessions_today.append(session)

    sessions_today_count = len(upcoming_or_ongoing_sessions_today)

    context = {
        'students_count': students_count,
        'teachers_count': teachers_count,
        'groups_count': groups_count,
        'sessions_today_count': sessions_today_count,
        'upcoming_or_ongoing_sessions_today': upcoming_or_ongoing_sessions_today
    }
    return render(request, 'school_app/home.html', context)

# Student views
def student_list(request):
    query = request.GET.get('q', '').strip()
    students_qs = Student.objects.all()  # Start with all students

    if query:
        # Search by full name, phone number, or card number
        students_qs = students_qs.filter(
            Q(full_name__icontains=query) |
            Q(phone_number__icontains=query) |
            Q(card_number__icontains=query)
        )

    students = students_qs.order_by('full_name') # Apply ordering after filtering
    context = {
        'students': students,
        'page_title': 'قائمة الطلاب',
        'search_query': query # Pass the query back to the template
    }
    return render(request, 'school_app/student_list.html', context)

def add_student(request):
    academic_levels = AcademicLevel.objects.all().order_by('category', 'name') # Ensure consistent order
    if request.method == 'POST':
        error_messages = []
        full_name = request.POST.get('full_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        guardian_phone = request.POST.get('guardian_phone', '').strip()

        birth_day_str = request.POST.get('birth_day')
        birth_month_str = request.POST.get('birth_month')
        birth_year_str = request.POST.get('birth_year')

        academic_level_id = request.POST.get('academic_level')
        registration_fee_paid = request.POST.get('registration_fee_paid') == 'on'

        # Validation
        if not full_name: error_messages.append("الاسم الكامل مطلوب.")
        if not phone_number: error_messages.append("رقم هاتف الطالب مطلوب.")
        # Basic phone validation (e.g., starts with 0, 10 digits) - adapt as needed
        if phone_number and (not phone_number.isdigit() or not len(phone_number) == 10 or not phone_number.startswith('0')):
            error_messages.append("رقم هاتف الطالب غير صالح (يجب أن يكون 10 أرقام ويبدأ بـ 0).")
        if not guardian_phone: error_messages.append("رقم هاتف الولي مطلوب.")
        if guardian_phone and (not guardian_phone.isdigit() or not len(guardian_phone) == 10 or not guardian_phone.startswith('0')):
            error_messages.append("رقم هاتف الولي غير صالح (يجب أن يكون 10 أرقام ويبدأ بـ 0).")

        birth_day, birth_month, birth_year = None, None, None
        try:
            if birth_day_str: birth_day = int(birth_day_str)
            if birth_month_str: birth_month = int(birth_month_str)
            if birth_year_str: birth_year = int(birth_year_str)

            if not (birth_day and birth_month and birth_year):
                error_messages.append("تاريخ الميلاد (اليوم، الشهر، السنة) مطلوب بالكامل.")
            else:
                if not (1 <= birth_day <= 31): error_messages.append("يوم الميلاد يجب أن يكون بين 1 و 31.")
                if not (1 <= birth_month <= 12): error_messages.append("شهر الميلاد يجب أن يكون بين 1 و 12.")
                current_year = datetime.date.today().year
                # Assuming students are typically between 3 and 70 years old
                if not (current_year - 70 <= birth_year <= current_year - 3):
                    error_messages.append(f"سنة الميلاد يجب أن تكون بين {current_year - 70} و {current_year - 3}.")
        except ValueError:
            error_messages.append("تاريخ الميلاد يجب أن يكون أرقامًا صحيحة.")

        if not academic_level_id: error_messages.append("المستوى الدراسي مطلوب.")

        academic_level = None
        if academic_level_id:
            try:
                academic_level = AcademicLevel.objects.get(id=academic_level_id)
            except AcademicLevel.DoesNotExist:
                error_messages.append("المستوى الدراسي المحدد غير صالح.")

        if error_messages:
            return render(request, 'school_app/add_student.html', {
                'academic_levels': academic_levels,
                'errors': error_messages, # Changed from 'error' to 'errors' for list
                'values': request.POST
            })

        # If all validation passes
        try:
            student = Student.objects.create(
                full_name=full_name,
                phone_number=phone_number,
                guardian_phone=guardian_phone,
                birth_day=birth_day,
                birth_month=birth_month,
                birth_year=birth_year,
                academic_level=academic_level,
                registration_fee_paid=registration_fee_paid
            )
            # Handle card number assignment
            # Generate a card number if not provided
            current_year = datetime.date.today().year
            student.card_number = f"CARD-{current_year}-{student.id:05d}"
            student.save()
            # log_action call removed for add_student

            # IMPORTANT: Redirect to the new enroll_student_in_groups view
            return redirect(reverse('enroll_student_in_groups', args=[student.id]))
        except IntegrityError: # Specifically catch IntegrityError
            error_messages.append("رقم هاتف الطالب المدخل موجود مسبقاً. يرجى استخدام رقم آخر.")
            return render(request, 'school_app/add_student.html', {
                'academic_levels': academic_levels,
                'errors': error_messages,
                'values': request.POST
            })
        except Exception as e:
            error_messages.append(f'حدث خطأ غير متوقع أثناء حفظ الطالب: {str(e)}')
            return render(request, 'school_app/add_student.html', {
                'academic_levels': academic_levels,
                'errors': error_messages,
                'values': request.POST
            })
    else: # GET request
        return render(request, 'school_app/add_student.html', {'academic_levels': academic_levels})

def search_student(request):
    query = request.GET.get('q', '').strip()
    students_results = Student.objects.none()
    page_title = "البحث عن طالب"

    if query:
        page_title = f"نتائج البحث عن: \"{query}\""

        # General search conditions for phone and card number
        other_conditions = Q(phone_number__icontains=query) | Q(card_number__icontains=query)

        # Name search logic
        query_words = query.split()
        name_conditions = Q()
        for word in query_words:
            name_conditions &= Q(full_name__icontains=word)

        # Also search by ID if the query is a number
        if query.isdigit():
            try:
                other_conditions |= Q(pk=int(query))
            except ValueError:
                pass

        # Combine name search with other searches using OR
        final_conditions = name_conditions | other_conditions

        students_results = Student.objects.filter(final_conditions).distinct().select_related('academic_level').order_by('full_name')

    context = {
        'query': query,
        'students_results': students_results,
        'page_title': page_title,
    }
    return render(request, 'school_app/search_student.html', context)

def student_detail(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    # Original enrolled_groups query, can be used as a base
    enrolled_groups_qs = Group.objects.filter(students=student).prefetch_related('subject', 'teacher', 'sessions__attendance_set')

    today = timezone.now().date()
    enrolled_groups_with_payment_stats = []

    for group in enrolled_groups_qs:
        price_per_session = Decimal('0.00')
        if group.price_per_4_sessions and group.price_per_4_sessions > 0:
            price_per_session = group.price_per_4_sessions / Decimal('4.0')

        try:
            student_group = StudentGroup.objects.get(student=student, group=group)
            enrollment_date = student_group.enrollment_date
        except StudentGroup.DoesNotExist:
            enrollment_date = None # Should not happen if student is in group.students.all()

        # Start with sessions up to today
        sessions_for_group_qs = group.sessions.filter(date__lte=today)
        if enrollment_date:
            sessions_for_group_qs = sessions_for_group_qs.filter(date__gte=enrollment_date)

        sessions_for_group_qs = sessions_for_group_qs.order_by('date', 'start_time')

        total_sessions_in_group = sessions_for_group_qs.count()
        paid_sessions_count = 0
        unpaid_non_excused_sessions_count = 0
        attended_and_paid_count = 0
        attended_not_paid_count = 0
        absent_and_paid_count = 0
        absent_not_paid_count = 0
        excused_absences_count = 0

        for session in sessions_for_group_qs:
            try:
                # Efficiently access prefetched attendance if possible, or query
                # Note: .get() will raise DoesNotExist if no record, .filter().first() returns None
                attendance_record = None
                # Accessing prefetched data requires careful iteration
                for att in session.attendance_set.all():
                    if att.student_id == student.id:
                        attendance_record = att
                        break
            except Attendance.DoesNotExist: # Should not happen with filter().first() or prefetched
                attendance_record = None

            if attendance_record:
                if attendance_record.student_paid_for_session:
                    paid_sessions_count += 1

                if attendance_record.excused_absence:
                    excused_absences_count += 1

                if attendance_record.present:
                    if attendance_record.student_paid_for_session:
                        attended_and_paid_count += 1
                    elif not attendance_record.excused_absence: # Present, not paid, not excused
                        attended_not_paid_count += 1
                        unpaid_non_excused_sessions_count += 1
                else: # Absent
                    if attendance_record.student_paid_for_session:
                        # This case implies student paid but was marked absent (and not excused)
                        absent_and_paid_count += 1
                    elif not attendance_record.excused_absence: # Absent, not paid, not excused
                        absent_not_paid_count += 1
                        unpaid_non_excused_sessions_count += 1
            else: # No attendance record for this past/current session
                  # Considered absent, not paid, not excused
                absent_not_paid_count += 1
                unpaid_non_excused_sessions_count += 1

        amount_due_for_group = unpaid_non_excused_sessions_count * price_per_session

        payment_status_display = "لا توجد حصص مستحقة" # Default
        if total_sessions_in_group > 0: # Only determine status if there are billable sessions
            if unpaid_non_excused_sessions_count == 0:
                if paid_sessions_count > 0 :
                     payment_status_display = "مدفوع بالكامل"
                else: # No unpaid, no paid -> could be all excused, or no sessions requiring payment yet
                    if excused_absences_count == total_sessions_in_group and total_sessions_in_group > 0:
                        payment_status_display = "جميع الغيابات معذورة"
                    elif total_sessions_in_group > 0: # Sessions exist but none are unpaid and none are paid (e.g. future, or all excused)
                        payment_status_display = "لا توجد مستحقات حالياً"
                    # If total_sessions_in_group is 0, it remains "لا توجد حصص مستحقة"
            elif unpaid_non_excused_sessions_count > 0 and paid_sessions_count > 0:
                payment_status_display = "مدفوع جزئياً"
            elif unpaid_non_excused_sessions_count > 0 and paid_sessions_count == 0:
                payment_status_display = "غير مدفوع"

        # For a group with no sessions yet (or all in future), total_sessions_in_group (filtered by lte today) would be 0.
        # In this case, unpaid_non_excused_sessions_count would also be 0.
        # The default "لا توجد حصص مستحقة" or a more specific "لا توجد حصص بعد" might be suitable.
        if total_sessions_in_group == 0 :
            payment_status_display = "لا توجد حصص بعد"

        remaining_future_paid_sessions_for_group = 0
        if price_per_session > Decimal('0.00'): # Ensure price_per_session is not zero
            if student.prepaid_balance > Decimal('0.00'): # Ensure student has prepaid balance
                remaining_future_paid_sessions_for_group = math.floor(student.prepaid_balance / price_per_session)
        else: # price_per_session is zero or negative, so no sessions can be paid
            remaining_future_paid_sessions_for_group = 0


        enrolled_groups_with_payment_stats.append({
            'group_id': group.id,
            'group_name': group.name,
            'subject_name': group.subject.name,
            'teacher_name': group.teacher.full_name,
            'price_per_4_sessions': group.price_per_4_sessions,
            'total_sessions_in_group': total_sessions_in_group, # Based on sessions <= today
            'paid_sessions_count': paid_sessions_count,
            'unpaid_non_excused_sessions_count': unpaid_non_excused_sessions_count,
            'attended_and_paid_count': attended_and_paid_count,
            'attended_not_paid_count': attended_not_paid_count,
            'absent_and_paid_count': absent_and_paid_count,
            'absent_not_paid_count': absent_not_paid_count,
            'excused_absences_count': excused_absences_count,
            'amount_due_for_group': amount_due_for_group,
            'payment_status_display': payment_status_display,
            'remaining_future_paid_sessions_for_group': remaining_future_paid_sessions_for_group,
            # Include original group object if needed in template for other attributes
            'group_obj': group
        })

    # The original attendance_records query might still be useful for a separate chronological list of all attendance
    # Or it can be removed if the per-group stats are sufficient.
    # For now, let's keep it but it's not directly used in the new stats logic.
    attendance_records = Attendance.objects.filter(student=student).select_related('session', 'session__group').order_by('-session__date', '-session__start_time')

    context = {
        'student': student,
        'enrolled_groups_with_payment_stats': enrolled_groups_with_payment_stats, # New context variable
        'attendance_records': attendance_records, # Kept for now
        'page_title': f"ملف الطالب: {student.full_name}"
    }
    return render(request, 'school_app/student_detail.html', context)

def enroll_student_in_groups(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    if request.method == 'POST':
        selected_group_ids = request.POST.getlist('groups_to_enroll')
        enrolled_count = 0
        for group_id_str in selected_group_ids:
            try:
                group_id = int(group_id_str)
                group_to_enroll = Group.objects.get(id=group_id)

                # Check if student is already in the group to prevent re-processing if form submitted multiple times
                if not StudentGroup.objects.filter(student=student, group=group_to_enroll).exists():
                    # Use timezone.now().date() for the enrollment_date
                    StudentGroup.objects.create(student=student, group=group_to_enroll, enrollment_date=timezone.now().date())
                    enrolled_count += 1
                else:
                    # Optionally, inform that student is already in this group, though not strictly an error
                    messages.info(request, f"الطالب مسجل بالفعل في الفوج {group_to_enroll.name}.")

            except (ValueError, Group.DoesNotExist):
                messages.error(request, f"الفوج المحدد بالرقم {group_id_str} غير صالح أو غير موجود.")
            except IntegrityError:
                messages.error(request, f"الطالب مسجل بالفعل في الفوج {group_to_enroll.name}.")
            except Exception as e: # Catch other potential errors
                messages.error(request, f"حدث خطأ أثناء تسجيل الطالب في الفوج {group_id_str}: {str(e)}")

        if enrolled_count > 0:
            messages.success(request, f"تم تسجيل الطالب {student.full_name} بنجاح في {enrolled_count} فوج/أفواج.")

        return redirect('student_detail', student_id=student.id)

    # GET request logic
    student_academic_level = student.academic_level
    enrolled_groups = student.group_set.all().select_related('subject', 'teacher') # Groups student is already in
    enrolled_group_ids = [group.id for group in enrolled_groups]

    # More refined logic considering academic level:
    # Groups that contain the student's academic level
    groups_matching_level = Group.objects.filter(academic_levels=student_academic_level)
    # Groups that have no academic level specified (open to all)
    groups_open_to_all = Group.objects.filter(academic_levels__isnull=True)
    # Combine these, exclude already enrolled, and ensure distinct results
    available_groups = (groups_matching_level | groups_open_to_all).exclude(id__in=enrolled_group_ids).distinct().select_related('subject', 'teacher').order_by('name')


    context = {
        'student': student,
        'available_groups': available_groups,
        'enrolled_groups': enrolled_groups, # Pass currently enrolled groups for display
        'page_title': f"تسجيل الطالب {student.full_name} في الأفواج"
    }
    return render(request, 'school_app/enroll_student_in_groups.html', context)

def delete_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        student_name = student.full_name # Get student name before deleting
        student_id_for_log = student.id # Capture ID before deletion
        student.delete()
        messages.success(request, f"تم حذف الطالب {student_name} بنجاح.")
        # log_action call removed for delete_student
        return HttpResponseRedirect(reverse_lazy('student_list'))
    # If GET or any other method, redirect to student list (or student_detail if preferred)
    # For simplicity, redirecting to student_list. A confirmation page is a good enhancement.
    return HttpResponseRedirect(reverse_lazy('student_list'))

def edit_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    academic_levels = AcademicLevel.objects.all().order_by('category', 'name')

    if request.method == 'POST':
        error_messages = []
        full_name = request.POST.get('full_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        guardian_phone = request.POST.get('guardian_phone', '').strip()

        birth_day_str = request.POST.get('birth_day')
        birth_month_str = request.POST.get('birth_month')
        birth_year_str = request.POST.get('birth_year')

        academic_level_id = request.POST.get('academic_level')
        # For checkbox, 'on' is sent if checked, otherwise not present in POST
        registration_fee_paid = request.POST.get('registration_fee_paid') == 'on'


        # Validation (similar to add_student, adapt as needed)
        if not full_name: error_messages.append("الاسم الكامل مطلوب.")
        if not phone_number: error_messages.append("رقم هاتف الطالب مطلوب.")
        if phone_number and (not phone_number.isdigit() or not len(phone_number) == 10 or not phone_number.startswith('0')):
            error_messages.append("رقم هاتف الطالب غير صالح (يجب أن يكون 10 أرقام ويبدأ بـ 0).")
        if not guardian_phone: error_messages.append("رقم هاتف الولي مطلوب.")
        if guardian_phone and (not guardian_phone.isdigit() or not len(guardian_phone) == 10 or not guardian_phone.startswith('0')):
            error_messages.append("رقم هاتف الولي غير صالح (يجب أن يكون 10 أرقام ويبدأ بـ 0).")

        birth_day, birth_month, birth_year = None, None, None
        try:
            if birth_day_str: birth_day = int(birth_day_str)
            if birth_month_str: birth_month = int(birth_month_str)
            if birth_year_str: birth_year = int(birth_year_str)

            if not (birth_day and birth_month and birth_year):
                error_messages.append("تاريخ الميلاد (اليوم، الشهر، السنة) مطلوب بالكامل.")
            else:
                if not (1 <= birth_day <= 31): error_messages.append("يوم الميلاد يجب أن يكون بين 1 و 31.")
                if not (1 <= birth_month <= 12): error_messages.append("شهر الميلاد يجب أن يكون بين 1 و 12.")
                current_year = datetime.date.today().year
                if not (current_year - 70 <= birth_year <= current_year - 3): # Assuming students are between 3 and 70
                    error_messages.append(f"سنة الميلاد يجب أن تكون بين {current_year - 70} و {current_year - 3}.")
        except ValueError:
            error_messages.append("تاريخ الميلاد يجب أن يكون أرقامًا صحيحة.")

        if not academic_level_id: error_messages.append("المستوى الدراسي مطلوب.")
        academic_level = None
        if academic_level_id:
            try:
                academic_level = AcademicLevel.objects.get(id=academic_level_id)
            except AcademicLevel.DoesNotExist:
                error_messages.append("المستوى الدراسي المحدد غير صالح.")

        # Phone number uniqueness check (excluding current student if unchanged)
        if phone_number != student.phone_number: # Only check if phone number has changed
            if Student.objects.filter(phone_number=phone_number).exists():
                error_messages.append("رقم هاتف الطالب المدخل موجود مسبقاً لطالب آخر.")

        if error_messages:
            # Repopulate values from request.POST for the template on error
            context = {
                'student': student, # Pass student to use its ID in form action
                'academic_levels': academic_levels,
                'errors': error_messages,
                'values': request.POST # This now includes all fields as submitted
            }
            return render(request, 'school_app/edit_student.html', context)

        # If all validation passes
        try:
            student.full_name = full_name
            student.phone_number = phone_number
            student.guardian_phone = guardian_phone
            student.birth_day = birth_day
            student.birth_month = birth_month
            student.birth_year = birth_year
            student.academic_level = academic_level
            student.registration_fee_paid = registration_fee_paid
            student.save()
            # log_action call removed for edit_student

            messages.success(request, "تم تحديث بيانات الطالب بنجاح.")
            return redirect(reverse('student_detail', args=[student.id]))
        except IntegrityError: # Should be caught by the specific check above, but as a safeguard
             error_messages.append("رقم هاتف الطالب المدخل موجود مسبقاً. يرجى استخدام رقم آخر.")
        except Exception as e:
            error_messages.append(f'حدث خطأ غير متوقع أثناء تحديث بيانات الطالب: {str(e)}')

        # If errors occurred during save (e.g., unexpected ones, or IntegrityError not caught above)
        context = {
            'student': student,
            'academic_levels': academic_levels,
            'errors': error_messages,
            'values': request.POST
        }
        return render(request, 'school_app/edit_student.html', context)

    else: # GET request
        # Pre-fill 'values' from the student object
        values = {
            'full_name': student.full_name,
            'phone_number': student.phone_number,
            'guardian_phone': student.guardian_phone,
            'birth_day': student.birth_day,
            'birth_month': student.birth_month,
            'birth_year': student.birth_year,
            'academic_level_id': student.academic_level.id if student.academic_level else '', # Use ID for select
            'registration_fee_paid': student.registration_fee_paid, # Boolean, template handles it
            'card_number': student.card_number, # Display card number
        }
        context = {
            'student': student,
            'academic_levels': academic_levels,
            'values': values,
            'page_title': f"تعديل بيانات الطالب: {student.full_name}"
        }
        return render(request, 'school_app/edit_student.html', context)

# Teacher views
def teacher_financial_detail(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)

    groups_with_uncompensated_sessions = []
    total_uncompensated_sessions_count = 0

    # Fetch all groups associated with the current teacher
    teacher_groups = Group.objects.filter(teacher=teacher).prefetch_related('sessions', 'subject')

    for group in teacher_groups:
        # Filter sessions for the current group where teacher_attended is True and teacher_compensated is False
        uncompensated_sessions = group.sessions.filter(teacher_attended=True, teacher_compensated=False).order_by('date', 'start_time')

        if uncompensated_sessions.exists():
            group_data = {
                'group_name': group.name,
                'subject_name': group.subject.name,
                'sessions': []
            }
            for session in uncompensated_sessions:
                # Optionally, count students present if needed, though might be complex here
                # For now, just session details
                group_data['sessions'].append({
                    'date': session.date,
                    'start_time': session.start_time.strftime("%H:%M"),
                    'duration': session.duration,
                    # 'students_present_count': session.attendance_set.filter(present=True).count() # Example if needed
                })
                total_uncompensated_sessions_count += 1
            groups_with_uncompensated_sessions.append(group_data)

    context = {
        'teacher': teacher,
        'groups_with_uncompensated_sessions': groups_with_uncompensated_sessions,
        'total_uncompensated_sessions_count': total_uncompensated_sessions_count,
        'page_title': f"التفاصيل المالية للمدرس: {teacher.full_name}"
    }
    return render(request, 'school_app/teacher_financial_detail.html', context)

def delete_teacher(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    if request.method == 'POST':
        teacher_name = teacher.full_name
        teacher_id_for_log = teacher.id # Capture ID before deletion
        try:
            # Deleting the teacher will now also delete associated groups
            # (and by extension, sessions of those groups due to Group.sessions relation cascade)
            teacher.delete()
            messages.success(request, f"تم حذف المدرس '{teacher_name}' وجميع الأفواج والحصص المتعلقة به بنجاح.")
            log_action('teacher_deleted', teacher_name, f"تم حذف المدرس {teacher_name}.")
        except Exception as e: # Catch any other unexpected error during deletion
            messages.error(request, f"حدث خطأ غير متوقع أثناء محاولة حذف المدرس: {str(e)}")
            # It might be better to redirect to teacher_list or a specific error page
            return HttpResponseRedirect(reverse_lazy('teacher_list'))
        return HttpResponseRedirect(reverse_lazy('teacher_list'))
    # For GET request, redirect to teacher list.
    return HttpResponseRedirect(reverse_lazy('teacher_list'))

def edit_teacher(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    subjects = Subject.objects.all().order_by('name')

    if request.method == 'POST':
        error_messages = []
        full_name = request.POST.get('full_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        subject_id = request.POST.get('subject')

        # Validation
        if not full_name: error_messages.append("الاسم الكامل للمعلم مطلوب.")
        if not phone_number: error_messages.append("رقم هاتف المعلم مطلوب.")
        if phone_number and (not phone_number.isdigit() or not len(phone_number) == 10 or not phone_number.startswith('0')):
            error_messages.append("رقم هاتف المعلم غير صالح (يجب أن يكون 10 أرقام ويبدأ بـ 0).")

        subject_obj = None
        if not subject_id:
            error_messages.append("مادة التدريس مطلوبة.")
        else:
            try:
                subject_obj = Subject.objects.get(id=subject_id)
            except Subject.DoesNotExist:
                error_messages.append("المادة المحددة غير صالحة.")

        # Phone number uniqueness check (excluding current teacher if unchanged)
        if phone_number != teacher.phone_number:
            if Teacher.objects.filter(phone_number=phone_number).exists():
                error_messages.append("رقم هاتف المعلم المدخل موجود مسبقاً لمعلم آخر.")

        if error_messages:
            context = {
                'teacher': teacher,
                'subjects': subjects,
                'errors': error_messages,
                'values': request.POST # Repopulate with submitted values
            }
            return render(request, 'school_app/edit_teacher.html', context)

        # If all validation passes
        try:
            teacher.full_name = full_name
            teacher.phone_number = phone_number
            teacher.subject = subject_obj
            teacher.save()
            # log_action call removed for edit_teacher

            messages.success(request, "تم تحديث بيانات المعلم بنجاح.")
            return redirect('teacher_list')
        except IntegrityError: # Should be caught by specific check, but as safeguard
            error_messages.append("رقم هاتف المعلم المدخل موجود مسبقاً. يرجى استخدام رقم آخر.")
        except Exception as e:
            error_messages.append(f'حدث خطأ غير متوقع أثناء تحديث بيانات المعلم: {str(e)}')

        # Render again with errors if save failed
        context = {
            'teacher': teacher,
            'subjects': subjects,
            'errors': error_messages,
            'values': request.POST
        }
        return render(request, 'school_app/edit_teacher.html', context)

    else: # GET request
        values = {
            'full_name': teacher.full_name,
            'phone_number': teacher.phone_number,
            'subject_id': teacher.subject.id if teacher.subject else ''
        }
        context = {
            'teacher': teacher,
            'subjects': subjects,
            'values': values,
            'page_title': f"تعديل بيانات المعلم: {teacher.full_name}"
        }
        return render(request, 'school_app/edit_teacher.html', context)

def teacher_list(request):
    query = request.GET.get('q', '').strip()
    teachers_qs = Teacher.objects.select_related('subject').all()

    if query:
        teachers_qs = teachers_qs.filter(
            Q(full_name__icontains=query) |
            Q(subject__name__icontains=query) # Search by subject name
        )

    teachers = teachers_qs.order_by('full_name')
    context = {
        'teachers': teachers,
        'page_title': "قائمة المعلمين",
        'search_query': query
    }
    return render(request, 'school_app/teacher_list.html', context)

def add_teacher(request):
    subjects = Subject.objects.all().order_by('name') # Ensure consistent order
    if request.method == 'POST':
        error_messages = []
        full_name = request.POST.get('full_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        subject_id = request.POST.get('subject')

        # Validation
        if not full_name: error_messages.append("الاسم الكامل للمعلم مطلوب.")
        if not phone_number: error_messages.append("رقم هاتف المعلم مطلوب.")
        if phone_number and (not phone_number.isdigit() or not len(phone_number) == 10 or not phone_number.startswith('0')):
            error_messages.append("رقم هاتف المعلم غير صالح (يجب أن يكون 10 أرقام ويبدأ بـ 0).")

        subject = None
        if not subject_id:
            error_messages.append("مادة التدريس مطلوبة.")
        else:
            try:
                subject = Subject.objects.get(id=subject_id)
            except Subject.DoesNotExist:
                error_messages.append("المادة المحددة غير صالحة.")

        if error_messages:
            return render(request, 'school_app/add_teacher.html', {
                'subjects': subjects,
                'errors': error_messages,
                'values': request.POST
            })

        try:
            new_teacher = Teacher.objects.create(
                full_name=full_name,
                phone_number=phone_number,
                subject=subject
            )
            log_action('teacher_added', f"{new_teacher.full_name}", f"تم إنشاء المدرس {new_teacher.full_name}.")
            return redirect('teacher_list')
        except IntegrityError: # Specifically catch IntegrityError
            error_messages.append("رقم هاتف المعلم المدخل موجود مسبقاً. يرجى استخدام رقم آخر.")
            return render(request, 'school_app/add_teacher.html', {
                'subjects': subjects,
                'errors': error_messages,
                'values': request.POST
            })
        except Exception as e:
            error_messages.append(f'حدث خطأ غير متوقع أثناء حفظ بيانات المعلم: {str(e)}')
            return render(request, 'school_app/add_teacher.html', {
                'subjects': subjects,
                'errors': error_messages,
                'values': request.POST
            })
    else: # GET request
        return render(request, 'school_app/add_teacher.html', {
            'subjects': subjects,
            'page_title': "إضافة معلم جديد"
        })

# Group views
def group_list(request):
    query = request.GET.get('q', '').strip()
    groups_qs = Group.objects.select_related('subject', 'teacher').prefetch_related('students', 'academic_levels')

    if query:
        groups_qs = groups_qs.filter(
            Q(name__icontains=query) |
            Q(subject__name__icontains=query) |
            Q(teacher__full_name__icontains=query)
        )

    groups = groups_qs.order_by('name')
    context = {
        'groups': groups,
        'page_title': 'قائمة الأفواج',
        'search_query': query
    }
    return render(request, 'school_app/group_list.html', context)

def add_group(request):
    subjects = Subject.objects.all()
    teachers = Teacher.objects.select_related('subject').all() # Maybe useful to show teacher's subject in dropdown
    academic_levels = AcademicLevel.objects.all()

    if request.method == 'POST':
        error_messages = [] # Use a list for potential errors
        try:
            data = json.loads(request.body)
            name = data.get('name')
            subject_id = data.get('subject')
            teacher_id = data.get('teacher')
            academic_level_ids = data.get('academic_levels')
            price_str = data.get('price_per_4_sessions')
            session_day_val = data.get('session_day') # Renamed for clarity
            # session_start_time = data.get('session_start_time') # Old way
            session_start_time_str = data.get('session_start_time')
            session_duration_str = data.get('session_duration', '1.5')
            is_continuous = data.get('is_continuous', False) # Get the value, default to False if not provided

            # Improved explicit validation for required fields
            if not name: error_messages.append('اسم الفوج مطلوب.')
            if not subject_id: error_messages.append('المادة مطلوبة.')
            if not teacher_id: error_messages.append('المدرس مطلوب.')
            if not academic_level_ids: error_messages.append('يجب تحديد مستوى دراسي واحد على الأقل.')
            if not price_str: error_messages.append('السعر مطلوب.')
            if session_day_val is None: # Crucial check for session_day, as 0 is a valid value for Monday
                error_messages.append('يوم الحصة الأسبوعية مطلوب.')
            # if not session_start_time: error_messages.append('وقت بداية الحصة مطلوب.') # Validation moved below
            # session_duration_str has a default, so it's unlikely to be missing unless explicitly sent as null/empty

            # --- Start of new validation block for session_start_time_str ---
            parsed_session_start_time = None
            if not session_start_time_str:
                error_messages.append('وقت بداية الحصة مطلوب.')
            else:
                try:
                    # Try parsing HH:MM first
                    parsed_session_start_time = datetime.datetime.strptime(session_start_time_str, '%H:%M').time()
                except ValueError:
                    try:
                        # If HH:MM fails, try HH:MM:SS
                        parsed_session_start_time = datetime.datetime.strptime(session_start_time_str, '%H:%M:%S').time()
                    except ValueError:
                        error_messages.append('تنسيق وقت بداية الحصة غير صالح. استخدم HH:MM أو HH:MM:SS.')
            # --- End of new validation block ---

            price_per_4_sessions = None
            if price_str: # Continue with other validations only if required fields seem present
                try:
                    price_per_4_sessions = Decimal(price_str)
                except ValueError:
                    error_messages.append('سعر الـ 4 حصص يجب أن يكون رقمًا صالحًا.')

            session_duration = None
            if session_duration_str:
                try:
                    session_duration = Decimal(session_duration_str)
                except ValueError:
                    error_messages.append('مدة الحصة يجب أن تكون رقمًا صالحًا.')

            subject = None
            if subject_id:
                try:
                    subject = Subject.objects.get(id=subject_id)
                except Subject.DoesNotExist:
                    error_messages.append('المادة المحددة غير صالحة.')

            teacher = None
            if teacher_id:
                try:
                    teacher = Teacher.objects.get(id=teacher_id)
                except Teacher.DoesNotExist:
                    error_messages.append('المدرس المحدد غير صالح.')

            # Optional: Validate academic_level_ids exist
            valid_academic_levels = []
            if academic_level_ids:
                for level_id in academic_level_ids:
                    try:
                        level = AcademicLevel.objects.get(id=level_id)
                        valid_academic_levels.append(level)
                    except AcademicLevel.DoesNotExist:
                        error_messages.append(f"المستوى الدراسي بالرقم {level_id} غير صالح.")
            else: # If academic_level_ids is empty or not provided
                 error_messages.append("يجب تحديد مستوى دراسي واحد على الأقل.")


            if error_messages:
                return JsonResponse({'status': 'error', 'error': ", ".join(error_messages)}, status=400)


            # Basic validation for teacher's subject (optional, but good practice)
            # if teacher.subject != subject:
            #     error_messages.append("The selected teacher does not teach the selected subject.")
            #     return JsonResponse({'status': 'error', 'error': ", ".join(error_messages)}, status=400)


            with transaction.atomic():
                group = Group.objects.create(
                    name=name,
                    subject=subject,
                    teacher=teacher,
                    price_per_4_sessions=price_per_4_sessions,
                    session_day=int(session_day_val), # Use the validated and correctly named variable
                    session_start_time=parsed_session_start_time, # USE THE PARSED TIME OBJECT
                    session_duration=session_duration,
                    is_continuous=is_continuous # Set the new field
                )
                group.academic_levels.set(valid_academic_levels)

                # Session Creation Logic
                try:
                    last_session_date_created = None
                    current_date = timezone.now().date()
                    target_weekday = group.session_day # 0=Monday, 6=Sunday

                    days_ahead = target_weekday - current_date.weekday()
                    if days_ahead < 0: # Target day already passed this week
                        days_ahead += 7
                    elif days_ahead == 0: # Target day is today
                        current_comparison_time = datetime.datetime.now().time()
                        logger.debug(f"Comparing times for group session scheduling: parsed_session_start_time='{parsed_session_start_time}' (type: {type(parsed_session_start_time)}) vs current_time='{current_comparison_time}' (type: {type(current_comparison_time)})")
                        # Check if session time for today has passed
                        if parsed_session_start_time and parsed_session_start_time <= current_comparison_time:
                            days_ahead += 7 # Schedule for next week

                    first_session_date = current_date + timedelta(days=days_ahead)

                    if group.is_continuous:
                        for i in range(40): # Create 40 sessions
                            session_date_for_loop = first_session_date + timedelta(weeks=i)
                            Session.objects.create(
                                group=group,
                                date=session_date_for_loop,
                                start_time=group.session_start_time,
                                duration=group.session_duration
                            )
                            last_session_date_created = session_date_for_loop
                    else: # Not continuous, create only one session
                        Session.objects.create(
                            group=group,
                            date=first_session_date,
                            start_time=group.session_start_time,
                            duration=group.session_duration
                        )
                        last_session_date_created = first_session_date

                    if last_session_date_created:
                        group.created_sessions_until = last_session_date_created
                        group.save(update_fields=['created_sessions_until'])

                except Exception as e_session:
                    logger.error(f"Error during automatic session creation for group {group.id if 'group' in locals() and hasattr(group, 'id') else 'Unknown'}: {str(e_session)}", exc_info=True)

                log_action('group_added', group.name, f"تم إنشاء الفوج {group.name} مع الحصص الأولية.")

            # messages.success(request, f"تم إنشاء الفوج '{group.name}' بنجاح.") # Keep for server logs if needed
            return JsonResponse({'status': 'success', 'message': f"تم إنشاء الفوج '{group.name}' والحصص الأولية بنجاح.", 'redirect_url': reverse('group_list')})

        except json.JSONDecodeError:
            error_msg = 'JSON خاطئ.'
            return JsonResponse({'status': 'error', 'error': error_msg}, status=400)
        except IntegrityError as e: # Catch potential database integrity issues
            error_msg = f'خطأ في قاعدة البيانات: {str(e)}'
            return JsonResponse({'status': 'error', 'error': error_msg}, status=400)
        except ValueError as ve: # Catch other ValueErrors (e.g. int conversion for session_day)
            error_msg = str(ve)
            return JsonResponse({'status': 'error', 'error': error_msg}, status=400)
        except Exception as e: # Catch all other errors
            error_msg = f'حدث خطأ غير متوقع: {str(e)}'
            # Log the exception e for server-side debugging
            return JsonResponse({'status': 'error', 'error': error_msg}, status=500)

    else: # GET request
        # This part remains the same as it serves the initial HTML form
        return render(request, 'school_app/add_group.html', {
            'subjects': subjects,
            'teachers': teachers,
            'academic_levels': academic_levels
        })

def group_detail(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    context = {
        'group': group,
        'page_title': f"تفاصيل الفوج: {group.name}"
    }
    return render(request, 'school_app/group_detail.html', context)

def edit_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    page_title = f"تعديل بيانات الفوج: {group.name}"

    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            updated_group = form.instance
            # log_action call removed for edit_group
            messages.success(request, "تم تحديث بيانات الفوج بنجاح.")
            return redirect(reverse('group_detail', args=[group.id]))
        # If form is not valid, it will be re-rendered with errors below
    else: # GET request
        form = GroupForm(instance=group)

    context = {
        'form': form,
        'group': group, # For using group.id in action URL and for page title
        'page_title': page_title
    }
    return render(request, 'school_app/edit_group.html', context)

def delete_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    if request.method == 'POST':
        group_name = group.name
        group_id_for_log = group.id # Capture ID before deletion
        group.delete() # Associated sessions will be deleted due to on_delete=models.CASCADE
        messages.success(request, f"تم حذف الفوج '{group_name}' وجميع حصصه المتعلقة بنجاح.")
        log_action('group_deleted', group_name, f"تم حذف الفوج {group_name}.")
        return HttpResponseRedirect(reverse_lazy('group_list'))
    # For GET or other methods, redirect to group list.
    # A confirmation page is better UX but this is simpler as per current pattern.
    return HttpResponseRedirect(reverse_lazy('group_list'))

def delete_session(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if request.method == 'POST':
        session_info = f"حصة الفوج '{session.group.name}' بتاريخ {session.date.strftime('%Y-%m-%d')}"
        session_id_for_log = session.id # Capture ID before deletion
        try:
            session.delete() # Associated attendance records will be deleted due to on_delete=models.CASCADE
            messages.success(request, f"تم حذف {session_info} بنجاح وجميع سجلات الحضور المتعلقة بها.")
            log_action('session_deleted', session_info, f"تم حذف {session_info}.")
        except Exception as e: # Catch any other unexpected error during deletion
            messages.error(request, f"حدث خطأ غير متوقع أثناء محاولة حذف الحصة: {str(e)}")
        return HttpResponseRedirect(reverse_lazy('session_list'))
    # For GET or other methods, redirect to session list.
    return HttpResponseRedirect(reverse_lazy('session_list'))

def edit_session(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    page_title = f"تعديل بيانات الحصة: {session.group.name} - {session.date}"

    if request.method == 'POST':
        form = SessionForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            updated_session = form.instance
            # log_action call removed for edit_session
            messages.success(request, "تم تحديث بيانات الحصة بنجاح.")
            return redirect('session_list')
        # If form is not valid, it will be re-rendered with errors
    else: # GET request
        form = SessionForm(instance=session)

    context = {
        'form': form,
        'session': session, # For action URL and page title context
        'page_title': page_title
    }
    return render(request, 'school_app/edit_session.html', context)

# Session views
def session_list(request):
    query = request.GET.get('q', '').strip()
    sessions_qs = Session.objects.select_related('group')

    if query:
        try:
            # Attempt to parse query as a date YYYY-MM-DD
            datetime.datetime.strptime(query, '%Y-%m-%d')
            sessions_qs = sessions_qs.filter(date=query)
        except ValueError:
            # If not a date, assume it's a group name query
            sessions_qs = sessions_qs.filter(group__name__icontains=query)

    sessions = sessions_qs.order_by('-date', '-start_time') # Apply ordering after filtering
    context = {
        'sessions': sessions,
        'page_title': 'قائمة الحصص',
        'search_query': query
    }
    return render(request, 'school_app/session_list.html', context)

def add_session(request):
    groups = Group.objects.all().order_by('name')
    page_title = "إضافة حصة جديدة"

    if request.method == 'POST':
        errors = []
        group_id = request.POST.get('group')
        date_str = request.POST.get('date')
        start_time_str = request.POST.get('start_time')
        duration_str = request.POST.get('duration')

        # Validation
        if not group_id: errors.append("الفوج مطلوب.")
        if not date_str: errors.append("التاريخ مطلوب.")
        if not start_time_str: errors.append("وقت البدء مطلوب.")
        if not duration_str: errors.append("المدة مطلوبة.")

        group = None
        if group_id:
            try:
                group = Group.objects.get(id=group_id)
            except Group.DoesNotExist:
                errors.append("الفوج المحدد غير صالح.")

        # Validate date format (YYYY-MM-DD)
        if date_str:
            try:
                datetime.datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                errors.append("تنسيق التاريخ غير صالح. استخدم YYYY-MM-DD.")

        # Validate time format (HH:MM)
        if start_time_str:
            try:
                datetime.datetime.strptime(start_time_str, '%H:%M')
            except ValueError:
                # Try HH:MM:SS as well, as some browsers might submit that
                try:
                    datetime.datetime.strptime(start_time_str, '%H:%M:%S')
                except ValueError:
                    errors.append("تنسيق وقت البدء غير صالح. استخدم HH:MM أو HH:MM:SS.")

        duration_decimal = None
        if duration_str:
            try:
                duration_decimal = Decimal(duration_str)
                if duration_decimal <= Decimal('0'):
                    errors.append("المدة يجب أن تكون رقمًا موجبًا.")
            except ValueError:
                errors.append("المدة يجب أن تكون رقمًا صالحًا.")

        if errors:
            return render(request, 'school_app/add_session.html', {
                'groups': groups,
                'errors': errors,
                'values': request.POST,
                'page_title': page_title,
                'selected_group_id': int(group_id) if group_id and group_id.isdigit() else None
            })

        # If validation passes
        try:
            new_session = Session.objects.create(
                group=group,
                date=date_str,
                start_time=start_time_str,
                duration=duration_decimal
            )
            log_action('session_added', f"{new_session.group.name} - {new_session.date}", f"تم إنشاء حصة للفوج {new_session.group.name} بتاريخ {new_session.date}.")
            messages.success(request, "تمت إضافة الحصة بنجاح.")
            return redirect('session_list')
        except Exception as e: # Catch any other unexpected errors during creation
            errors.append(f"حدث خطأ غير متوقع أثناء إنشاء الحصة: {str(e)}")
            return render(request, 'school_app/add_session.html', {
                'groups': groups,
                'errors': errors,
                'values': request.POST,
                'page_title': page_title,
                'selected_group_id': int(group_id) if group_id and group_id.isdigit() else None
            })

    # For GET request:
    selected_group_id = request.GET.get('group_id')
    selected_group_id_int = None
    if selected_group_id and selected_group_id.isdigit():
        selected_group_id_int = int(selected_group_id)

    context = {
        'page_title': page_title,
        'groups': groups,
        'selected_group_id': selected_group_id_int
    }
    return render(request, 'school_app/add_session.html', context)

def manage_session_attendance(request, session_id):
    session = get_object_or_404(Session.objects.select_related('group__subject', 'group__teacher'), id=session_id)
    students_in_group = session.group.students.all().order_by('full_name')
    page_title = f"إدارة حضور حصة: {session.group.name} - {session.date.strftime('%Y-%m-%d')}"

    if request.method == 'POST':
        for student in students_in_group:
            is_present_from_form = request.POST.get(f'student_{student.id}_present') == 'on'
            is_paid_from_form = request.POST.get(f'student_{student.id}_paid') == 'on'
            # Optional: student_absent_and_forced_paid logic
            # student_absent_and_forced_paid_from_form = request.POST.get(f'student_{student.id}_force_paid') == 'on'

            defaults_for_update = {
                'present': is_present_from_form,
                'student_paid_for_session': is_paid_from_form
            }
            # if not is_present_from_form and student_absent_and_forced_paid_from_form:
            #     defaults_for_update['student_paid_for_session'] = True
            #     defaults_for_update['student_absent_and_forced_paid'] = True
            # else:
            #     defaults_for_update['student_absent_and_forced_paid'] = False


            Attendance.objects.update_or_create(
                student=student,
                session=session,
                defaults=defaults_for_update
            )
        # log_action call removed for manage_session_attendance
        messages.success(request, "تم تحديث سجلات الحضور والدفع بنجاح.")
        return redirect('manage_session_attendance', session_id=session.id)

    # GET request logic
    existing_attendance_records = Attendance.objects.filter(session=session)
    attendance_data_map = {att.student_id: {
        'present': att.present,
        'paid': att.student_paid_for_session,
        'attendance_id': att.id
        # 'force_paid': att.student_absent_and_forced_paid # If using this feature
    } for att in existing_attendance_records}

    student_attendance_list = []
    for student in students_in_group:
        data = attendance_data_map.get(student.id, {})
        student_attendance_list.append({
            'student_id': student.id,
            'student_name': student.full_name,
            'is_present': data.get('present', False),
            'is_paid': data.get('paid', False)
            # 'is_force_paid': data.get('force_paid', False) # If using this feature
        })

    context = {
        'session': session,
        'student_attendance_list': student_attendance_list,
        'page_title': page_title
    }
    return render(request, 'school_app/manage_session_attendance.html', context)


def session_attendance_detail(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    present_students = Student.objects.filter(attendance__session=session, attendance__present=True)
    absent_students = Student.objects.filter(attendance__session=session, attendance__present=False, attendance__excused_absence=False)
    excused_students = Student.objects.filter(attendance__session=session, attendance__excused_absence=True)

    # Get all students in the group
    group_students = session.group.students.all()

    # Get students with attendance records
    students_with_attendance = present_students | absent_students | excused_students

    # Get students without attendance records (who were absent and not marked)
    students_without_attendance = group_students.exclude(id__in=students_with_attendance.values('id'))


    context = {
        'session': session,
        'present_students': present_students,
        'absent_students': absent_students | students_without_attendance,
        'excused_students': excused_students,
        'page_title': f"سجل حضور حصة: {session.group.name} - {session.date.strftime('%Y-%m-%d')}"
    }
    return render(request, 'school_app/session_attendance_detail.html', context)


# Attendance views
def attendance_register(request):
    today = timezone.now().date()
    sessions = Session.objects.filter(date=today).select_related('group').order_by('group__name', 'start_time')
    # students list removed, it will be populated by JS
    context = {
        'sessions': sessions,
        'page_title': f"تسجيل الحضور والغياب ليوم {today.strftime('%Y-%m-%d')}"
    }
    return render(request, 'school_app/attendance_register.html', context)


def attendance_record(request):
    today = timezone.now().date()

    # Get groups that have sessions today
    groups_with_sessions_today_ids = Session.objects.filter(date=today).values_list('group_id', flat=True).distinct()
    groups_for_today = Group.objects.filter(id__in=groups_with_sessions_today_ids).order_by('name')

    selected_group_id = request.GET.get('group_id')
    selected_group = None
    present_students = []
    absent_students = []

    if selected_group_id:
        try:
            selected_group = get_object_or_404(Group, id=selected_group_id)
            # Find all sessions for this group today
            sessions_for_group_today = Session.objects.filter(group=selected_group, date=today)
            if sessions_for_group_today.exists():
                # Get all students enrolled in the group
                all_students_in_group = selected_group.students.all()

                # Get all attendance records for this group's sessions today
                attendance_records = Attendance.objects.filter(session__in=sessions_for_group_today)

                present_student_ids = attendance_records.filter(present=True).values_list('student_id', flat=True)

                # Students are present if they attended at least one session today
                present_students = all_students_in_group.filter(id__in=present_student_ids)

                # Absent students are those in the group who are not in the present list
                absent_students = all_students_in_group.exclude(id__in=present_student_ids)

        except (ValueError, Group.DoesNotExist):
            messages.error(request, "الفوج المحدد غير صالح.")


    context = {
        'page_title': "سجل الحضور اليومي",
        'groups_for_today': groups_for_today,
        'selected_group': selected_group,
        'present_students': present_students,
        'absent_students': absent_students,
    }
    return render(request, 'school_app/attendance_record.html', context)


import json # Make sure json is imported

def api_record_attendance(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'طلب غير صالح. يُسمح فقط بطلبات POST.'}, status=405)

    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        student_identifier = data.get('student_id') # Can be PK or card_number
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'بيانات JSON غير صالحة.'}, status=400)

    if not session_id or not student_identifier:
        return JsonResponse({'status': 'error', 'message': 'معرف الجلسة ومعرف الطالب مطلوبان.'}, status=400)

    try:
        session = Session.objects.get(id=session_id)
    except Session.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'الجلسة غير موجودة.'}, status=404)

    student = None
    # Try finding by PK if identifier is purely numeric string or an actual integer
    if isinstance(student_identifier, int) or (isinstance(student_identifier, str) and student_identifier.isdigit()):
        try:
            student = Student.objects.get(pk=int(student_identifier))
        except Student.DoesNotExist:
            # If not found by PK, and it was a numeric string, we might still want to try it as a card_number below.
            # So, we 'pass' here and let the next block handle it if student is still None.
            pass

    # If not found by PK (or if identifier wasn't purely numeric), try by card_number.
    # This also handles the case where a numeric student_identifier (e.g. "123") failed PK lookup
    # and should be tried as a card_number.
    if not student and isinstance(student_identifier, str):
        try:
            student = Student.objects.get(card_number=student_identifier)
        except Student.DoesNotExist:
            pass # Not found by card_number either
    elif not student and isinstance(student_identifier, int): # If it was an int, and not found by PK
        try:
            student = Student.objects.get(card_number=str(student_identifier))
        except Student.DoesNotExist:
            pass


    if not student:
        return JsonResponse({'status': 'error', 'message': 'الطالب غير موجود. تحقق من الرقم المدخل أو البطاقة.'}, status=404)

    try:
        attendance, created = Attendance.objects.get_or_create(
            student=student,
            session=session
        )

        if not created and attendance.present:
            return JsonResponse({
                'status': 'already_registered',
                'message': f'الطالب {student.full_name} مسجل بالفعل في هذه الحصة.',
                'student_name': student.full_name,
                'session_info': f'{session.group.name} - {session.date} {session.start_time.strftime("%H:%M")}'
            }, status=200)

        attendance.present = True

        # --- Payment Logic ---
        payment_status_message = "الحصة غير مدفوعة" # Default message
        group = session.group
        price_per_session = Decimal('0.00')

        if group.price_per_4_sessions and group.price_per_4_sessions > 0:
            price_per_session = group.price_per_4_sessions / Decimal('4.0')

        if price_per_session > 0:
            if not attendance.student_paid_for_session and student.prepaid_balance >= price_per_session:
                student.prepaid_balance -= price_per_session
                attendance.student_paid_for_session = True
                student.save(update_fields=['prepaid_balance'])
                payment_status_message = f"تم الدفع من الرصيد المسبق. الرصيد المتبقي: {student.prepaid_balance.quantize(Decimal('0.01'))} دج"
            elif attendance.student_paid_for_session:
                payment_status_message = "الحصة مدفوعة بالفعل"
            else: # Not enough balance
                payment_status_message = f"رصيد غير كافٍ. الرصيد الحالي: {student.prepaid_balance.quantize(Decimal('0.01'))} دج"
        elif attendance.student_paid_for_session:
             payment_status_message = "الحصة مدفوعة بالفعل"
        else: # Price is zero
             payment_status_message = "الحصة مجانية (السعر 0)"

        attendance.save()


        # Calculate unpaid sessions for the student in this group
        try:
            student_group = StudentGroup.objects.get(student=student, group=session.group)
            enrollment_date = student_group.enrollment_date
        except StudentGroup.DoesNotExist:
            enrollment_date = None

        unpaid_sessions_count = 0
        if enrollment_date:
            unpaid_sessions_count = Attendance.objects.filter(
                student=student,
                session__group=session.group,
                session__date__gte=enrollment_date,
                student_paid_for_session=False,
                excused_absence=False
            ).count()

        return JsonResponse({
            'status': 'success',
            'message': 'تم تسجيل الحضور بنجاح.',
            'student_name': student.full_name,
            'session_info': f'{session.group.name} - {session.date} {session.start_time.strftime("%H:%M")}',
            'payment_status': payment_status_message, # Use the dynamic message
            'attendance_time': attendance.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'unpaid_sessions_count': unpaid_sessions_count
        }, status=201)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'حدث خطأ غير متوقع: {str(e)}'}, status=500)

# Payment views
def student_payment(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    page_title = f"مدفوعات الطالب: {student.full_name}"

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'pay_registration_fee':
            if not student.registration_fee_paid:
                student.registration_fee_paid = True
                # Consider adding a date field for when registration fee was paid, e.g., student.registration_payment_date = timezone.now()
                student.save()
                # log_action call removed for student_payment (registration_fee_paid)
                messages.success(request, "تم تسجيل دفع رسوم التسجيل الأولية بنجاح.")
            else:
                messages.info(request, "رسوم التسجيل الأولية مدفوعة بالفعل.")
            return redirect('student_payment', student_id=student_id)

        elif action == 'pay_group_sessions':
            group_id = request.POST.get('group_id')
            sessions_to_pay_count_str = request.POST.get('sessions_to_pay', '0')
            try:
                sessions_to_pay_count = int(sessions_to_pay_count_str)
                group_to_pay_for = get_object_or_404(Group, id=group_id)

                if sessions_to_pay_count <= 0:
                    messages.error(request, "عدد الحصص للدفع يجب أن يكون أكبر من صفر.")
                else:
                    # Get all sessions for this student in this group, ordered by date
                    # We want to pay for the earliest unpaid sessions first.
                    student_group_sessions = Session.objects.filter(group=group_to_pay_for).order_by('date', 'start_time')

                    paid_this_transaction_count = 0
                    sessions_marked_paid_info = []

                    for session_obj in student_group_sessions:
                        if paid_this_transaction_count >= sessions_to_pay_count:
                            break # Paid enough sessions for this transaction

                        attendance, created = Attendance.objects.get_or_create(
                            student=student,
                            session=session_obj,
                            defaults={'present': False} # Default to absent if no record, payment can still be made
                        )

                        if not attendance.student_paid_for_session:
                            attendance.student_paid_for_session = True
                            # attendance.student_absent_and_forced_paid = not attendance.present # Optional: if student was absent, mark as forced paid
                            attendance.save()
                            paid_this_transaction_count += 1
                            sessions_marked_paid_info.append(f"{session_obj.date.strftime('%Y-%m-%d')} ({session_obj.start_time.strftime('%H:%M')})")

                    if paid_this_transaction_count > 0:
                        messages.success(request, f"تم تسجيل دفع {paid_this_transaction_count} حصة/حصص بنجاح للفوج {group_to_pay_for.name}.")
                        # log_action call removed for student_payment (group_session_payment_processed)
                        # For more detail: messages.info(request, f"الحصص التي تم دفعها: {', '.join(sessions_marked_paid_info)}")
                    elif sessions_to_pay_count > 0 : # Attempted to pay but none were eligible
                        messages.info(request, f"لا توجد حصص غير مدفوعة لتسجيلها حالياً للفوج {group_to_pay_for.name}.")
                    else: # Should be caught by sessions_to_pay_count <= 0, but as a fallback
                        messages.warning(request, "لم يتم تحديد عدد حصص للدفع.")


            except ValueError:
                messages.error(request, "عدد الحصص المدخل غير صالح.")
            except Group.DoesNotExist:
                messages.error(request, "الفوج المحدد للدفع غير موجود.")

            return redirect('student_payment', student_id=student_id)

    # GET request logic:
    payment_info_by_group = []
    # Prefetch related sessions and their attendance records for the current student to optimize queries
    enrolled_groups = student.group_set.all().prefetch_related(
        'sessions__attendance_set', # Prefetch attendance for each session
        'subject',
        'teacher'
    )

    for group in enrolled_groups:
        # All sessions for the group, ordered
        group_sessions_qs = group.sessions.all().order_by('date', 'start_time')

        group_total_sessions_count = group_sessions_qs.count()
        group_paid_sessions_count = 0
        group_unpaid_sessions_count = 0 # Specifically sessions that have an attendance record and are unpaid OR no attendance record yet

        group_attended_and_paid_count = 0
        group_attended_not_paid_count = 0
        group_absent_but_paid_count = 0
        group_absent_not_paid_count = 0 # Includes sessions with no attendance record yet (assumed absent, not paid)

        session_payment_details_list = []

        for session_obj in group_sessions_qs:
            # Try to find the specific attendance record for THIS student and THIS session
            # This was potentially inefficient if done per session without prefetching.
            # With prefetch_related('sessions__attendance_set'), this should be more optimized.
            current_session_attendance = None
            for att_record in session_obj.attendance_set.all(): # Iterate through prefetched attendance
                if att_record.student_id == student.id:
                    current_session_attendance = att_record
                    break

            is_present = False
            is_paid = False
            attendance_status_display = "لم يحضر/يسجل" # Default if no attendance record
            payment_status_display = "غير مدفوعة"   # Default if no attendance record

            if current_session_attendance:
                is_present = current_session_attendance.present
                is_paid = current_session_attendance.student_paid_for_session
                attendance_status_display = "حاضر" if is_present else "غائب"
                payment_status_display = "مدفوعة" if is_paid else "غير مدفوعة"

                if is_paid:
                    group_paid_sessions_count += 1
                    if is_present:
                        group_attended_and_paid_count += 1
                    else:
                        group_absent_but_paid_count += 1
                else: # Not paid (but attendance record exists)
                    group_unpaid_sessions_count += 1
                    if is_present:
                        group_attended_not_paid_count += 1
                    else:
                        group_absent_not_paid_count += 1
            else: # No attendance record for this student and session
                group_unpaid_sessions_count += 1 # Count as unpaid
                group_absent_not_paid_count += 1 # And absent
                # attendance_status_display and payment_status_display remain as defaults

            session_payment_details_list.append({
                'id': session_obj.id,
                'date': session_obj.date,
                'start_time': session_obj.start_time.strftime("%H:%M"),
                'attendance_status': attendance_status_display,
                'payment_status': payment_status_display,
                'is_paid': is_paid,
            })

        payment_info_by_group.append({
            'group_id': group.id,
            'group_name': group.name,
            'subject_name': group.subject.name,
            'teacher_name': group.teacher.full_name,
            'price_per_4_sessions': group.price_per_4_sessions,
            'total_sessions_in_group': group_total_sessions_count,
            'paid_session_count': group_paid_sessions_count,
            'unpaid_session_count': group_unpaid_sessions_count,
            'attended_not_paid_count': group_attended_not_paid_count,
            'attended_and_paid_count': group_attended_and_paid_count,
            'absent_but_paid_count': group_absent_but_paid_count,
            'absent_not_paid_count': group_absent_not_paid_count,
            'session_details': session_payment_details_list,
        })

    context = {
        'student': student,
        'payment_info_by_group': payment_info_by_group,
        'registration_fee_paid': student.registration_fee_paid,
        'REGISTRATION_FEE_AMOUNT': REGISTRATION_FEE_AMOUNT,
        'page_title': page_title
    }
    return render(request, 'school_app/student_payment.html', context)

# from django.utils import timezone # Ensure timezone is imported if not already - REMOVED, MOVED TO TOP

def print_registration_fee_confirmation(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    # REGISTRATION_FEE_AMOUNT is already defined globally in this file.

    # Optional: Check if fee is paid, though template logic should prevent button if not.
    if not student.registration_fee_paid:
        messages.error(request, "رسوم التسجيل لهذا الطالب لم يتم دفعها بعد.")
        return redirect('student_detail', student_id=student.id)

    context = {
        'student': student,
        'REGISTRATION_FEE_AMOUNT': REGISTRATION_FEE_AMOUNT,
        'print_date': timezone.now(),
        # No base.html extension for this template, it's a standalone print page.
    }
    return render(request, 'school_app/print_registration_confirmation.html', context)

# Define a constant for teacher pay per session, or calculate it based on group fees
TEACHER_PAY_PER_SESSION_AMOUNT = Decimal('500.00') # Placeholder flat rate

def teacher_payment(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    page_title = f"دفع مستحقات المدرس: {teacher.full_name}"

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'pay_teacher_sessions':
            group_id = request.POST.get('group_id')
            sessions_to_compensate_count_str = request.POST.get('sessions_to_compensate_count', '0')

            try:
                sessions_to_compensate_count = int(sessions_to_compensate_count_str)
                group_to_compensate_for = get_object_or_404(Group, id=group_id, teacher=teacher)

                if sessions_to_compensate_count <= 0:
                    messages.error(request, "عدد الحصص للدفع يجب أن يكون أكبر من صفر.")
                else:
                    # Get uncompensated sessions for this teacher in this group where teacher attended
                    sessions_to_update = Session.objects.filter(
                        group=group_to_compensate_for,
                        teacher_attended=True,
                        teacher_compensated=False
                    ).order_by('date', 'start_time')[:sessions_to_compensate_count]

                    updated_count = 0
                    for session_obj in sessions_to_update:
                        session_obj.teacher_compensated = True
                        session_obj.save()
                        updated_count += 1

                    if updated_count > 0:
                        messages.success(request, f"تم تسجيل دفع مستحقات لـ {updated_count} حصة/حصص للمدرس {teacher.full_name} في الفوج {group_to_compensate_for.name}.")
                        # log_action call removed for teacher_payment
                    else:
                        messages.info(request, "لا توجد حصص مستحقة للدفع حالياً (تأكد من تسجيل حضور المدرس أولاً).")

            except ValueError:
                messages.error(request, "عدد الحصص المدخل غير صالح.")
            except Group.DoesNotExist:
                messages.error(request, "الفوج المحدد غير صحيح أو لا يتبع لهذا المدرس.")
            return redirect('teacher_payment', teacher_id=teacher_id)

    # GET request logic
    payment_info_by_group = []
    taught_groups = Group.objects.filter(teacher=teacher).prefetch_related('sessions', 'subject')

    for group in taught_groups:
        group_sessions_qs = group.sessions.all().order_by('date', 'start_time')

        total_sessions_in_group = group_sessions_qs.count()
        compensated_session_count = 0
        uncompensated_session_count = 0 # All uncompensated sessions for this group
        attended_and_compensated_count = 0
        attended_not_compensated_count = 0 # Attended by teacher but not yet compensated
        teacher_attended_total_count = 0


        session_details_list = []

        for session_obj in group_sessions_qs:
            teacher_attended_status = session_obj.teacher_attended if session_obj.teacher_attended is not None else False

            if teacher_attended_status:
                teacher_attended_total_count +=1

            if session_obj.teacher_compensated:
                compensated_session_count += 1
                if teacher_attended_status:
                    attended_and_compensated_count += 1
            else: # Not compensated
                uncompensated_session_count += 1
                if teacher_attended_status:
                    attended_not_compensated_count += 1

            session_details_list.append({
                'id': session_obj.id,
                'date': session_obj.date,
                'start_time': session_obj.start_time.strftime("%H:%M"),
                'teacher_attended': teacher_attended_status,
                'teacher_compensated': session_obj.teacher_compensated,
            })

        payment_info_by_group.append({
            'group_id': group.id,
            'group_name': group.name,
            'subject_name': group.subject.name,
            'total_sessions_in_group': total_sessions_in_group,
            'teacher_attended_total_count': teacher_attended_total_count,
            'compensated_session_count': compensated_session_count, # Total compensated for this group
            'uncompensated_session_count': uncompensated_session_count, # Total uncompensated for this group
            'attended_and_compensated_count': attended_and_compensated_count,
            'attended_not_compensated_count': attended_not_compensated_count, # Key for form: sessions eligible for payment
            'session_details': session_details_list,
        })

    context = {
        'teacher': teacher,
        'payment_info_by_group': payment_info_by_group,
        'TEACHER_PAY_PER_SESSION_AMOUNT': TEACHER_PAY_PER_SESSION_AMOUNT, # Placeholder for display
        'page_title': page_title
    }
    return render(request, 'school_app/teacher_payment.html', context)

# from django.utils import timezone # For default dates - REMOVED, MOVED TO TOP
# from decimal import Decimal # Explicit import for Decimal - REMOVED, MOVED TO TOP

# Basic imports required for the new view (some might be duplicates of existing ones but ensures presence)
from .models import Teacher, Group, Session # Already likely imported, but good to ensure for the new view
from django.shortcuts import render, get_object_or_404 # Also likely, but ensure

REGISTRATION_FEE_AMOUNT = Decimal('500.00') # Updated registration fee
TEACHER_SESSION_PAY_RATE = Decimal('0.7') # Placeholder for teacher's share of session fee

def payment_report(request):
    today = timezone.now().date()
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    period_type = request.GET.get('period', 'current_month') # Default to current_month

    start_date = None
    end_date = None
    errors = []
    report_period_display = ""

    if period_type == 'custom' and start_date_str and end_date_str:
        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            errors.append("تنسيق تاريخ البدء غير صالح. استخدم YYYY-MM-DD.")
        try:
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            errors.append("تنسيق تاريخ الانتهاء غير صالح. استخدم YYYY-MM-DD.")
        if start_date and end_date and start_date > end_date:
            errors.append("تاريخ البدء لا يمكن أن يكون بعد تاريخ الانتهاء.")
    elif period_type == 'current_month':
        start_date = today.replace(day=1)
        end_date = today
    elif period_type == 'last_month':
        first_day_current_month = today.replace(day=1)
        end_date = first_day_current_month - datetime.timedelta(days=1)
        start_date = end_date.replace(day=1)
    elif period_type == 'current_year':
        start_date = today.replace(month=1, day=1)
        end_date = today
    # Add other period types as needed, e.g., last_30_days, specific quarter

    if errors: # If parsing errors, default to current month and show errors
        start_date = today.replace(day=1)
        end_date = today
        # It might be better to redirect or render with an error message specific to date parsing
        # For now, just fall back to default period.

    months_ar = {
        1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل', 5: 'مايو', 6: 'يونيو',
        7: 'يوليو', 8: 'أغسطس', 9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'
    }

    if period_type != 'custom' and not (start_date_str or end_date_str):
        month_name = months_ar[start_date.month]
        year = start_date.year

        if period_type == 'current_month':
            report_period_display = f"الشهر الحالي ({month_name} {year})"
        elif period_type == 'last_month':
            report_period_display = f"الشهر الماضي ({month_name} {year})"
        elif period_type == 'current_year':
            report_period_display = f"السنة الحالية ({year})"


    # Initialize financial figures
    income_from_registration = Decimal('0.00')
    income_from_sessions = Decimal('0.00')
    total_expenses = Decimal('0.00') # Primarily teacher payments for now

    # Calculate Income from Registration Fees
    # Assuming registration_fee_paid means it was paid around student.created_at
    # This is a simplification. A dedicated Payment model would be better.
    students_registered_in_period = Student.objects.filter(registration_fee_paid=True)
    if start_date and end_date:
        # Adjust end_date to include the whole day for created_at (DateTimeField)
        effective_end_date = datetime.datetime.combine(end_date, datetime.time.max)
        students_registered_in_period = students_registered_in_period.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)

    # Explicitly cast count to Decimal for type consistency in multiplication
    income_from_registration = Decimal(students_registered_in_period.count()) * REGISTRATION_FEE_AMOUNT

    # Calculate Income from Sessions
    paid_attendances = Attendance.objects.filter(student_paid_for_session=True).select_related('session__group')
    if start_date and end_date:
        paid_attendances = paid_attendances.filter(session__date__gte=start_date, session__date__lte=end_date)

    for att in paid_attendances:
        if att.session.group and att.session.group.price_per_4_sessions > 0:
            price_per_session = att.session.group.price_per_4_sessions / Decimal('4.0')
            income_from_sessions += price_per_session

    # Calculate Total Expenses (Teacher Payments)
    compensated_sessions = Session.objects.filter(teacher_compensated=True)
    if start_date and end_date:
        compensated_sessions = compensated_sessions.filter(date__gte=start_date, date__lte=end_date)

    # Sum the actual amounts paid to teachers from the new field
    total_expenses_agg = compensated_sessions.aggregate(total=Sum('teacher_payment_amount'))
    total_expenses = total_expenses_agg['total'] or Decimal('0.00')

    total_income = income_from_registration + income_from_sessions
    net_income = total_income - total_expenses

    # Calculate Income by Group
    income_by_group_data = []
    all_groups = Group.objects.select_related('subject', 'teacher').all()

    for group in all_groups:
        group_income = Decimal('0.00')
        group_attendances = Attendance.objects.filter(
            session__group=group,
            student_paid_for_session=True
        )
        if start_date and end_date:
            group_attendances = group_attendances.filter(session__date__gte=start_date, session__date__lte=end_date)

        for att in group_attendances:
            if group.price_per_4_sessions > 0: # Ensure price is set
                price_per_session = group.price_per_4_sessions / Decimal('4.0')
                group_income += price_per_session

        if group_income > 0: # Only include groups with income in the report for this period
            income_by_group_data.append({
                'name': group.name,
                'subject_name': group.subject.name,
                'teacher_name': group.teacher.full_name,
                'income': group_income
            })

    # Sort by income, descending
    income_by_group_data.sort(key=lambda x: x['income'], reverse=True)

    # Additional Statistics
    new_students_count = 0
    new_groups_count = 0
    completed_sessions_count = 0

    if start_date and end_date:
        effective_end_date_for_created_at = datetime.datetime.combine(end_date, datetime.time.max)

        new_students_count = Student.objects.filter(
            created_at__gte=start_date,
            created_at__lte=effective_end_date_for_created_at
        ).count()

        new_groups_count = Group.objects.filter(
            created_at__gte=start_date,
            created_at__lte=effective_end_date_for_created_at
        ).count()

        completed_sessions_count = Session.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).count()
        # Optional: Refine completed_sessions_count to only include sessions in the past
        # or where teacher_attended is True, if that field is reliably used.
        # For now, all sessions within the period are counted.

    context = {
        'page_title': 'تقرير المدفوعات',
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
        'report_period_display': report_period_display,
        'total_income': total_income,
        'income_from_registration': income_from_registration,
        'income_from_sessions': income_from_sessions,
        'total_expenses': total_expenses,
        'net_income': net_income,
        'income_by_group_data': income_by_group_data,
        'new_students_count': new_students_count,
        'new_groups_count': new_groups_count,
        'completed_sessions_count': completed_sessions_count,
        'errors': errors, # Pass any date parsing errors to the template
        'period_type_selected': period_type, # To re-select the period dropdown
        'start_date_selected': start_date_str, # To repopulate custom date fields
        'end_date_selected': end_date_str,     # To repopulate custom date fields
    }
    # log_action call removed for payment_report
    return render(request, 'school_app/payment_report.html', context)

def action_log_list(request):
    log_list = ActionLog.objects.all().order_by('-action_time') # Already ordered in Meta, but good to be explicit

    # Pagination: Show 50 logs per page (adjust as needed)
    paginator = Paginator(log_list, 50)
    page_number = request.GET.get('page')
    try:
        logs = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        logs = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        logs = paginator.page(paginator.num_pages)

    context = {
        'logs': logs,
        'page_title': 'سجل الإجراءات'
    }
    return render(request, 'school_app/action_log_list.html', context)

# API endpoints for frontend
def api_academic_levels(request):
    levels = AcademicLevel.objects.all()
    data = [{
        'id': level.id,
        'name': level.name,
        'category': level.category
    } for level in levels]
    return JsonResponse(data, safe=False)

def api_subjects(request):
    subjects = Subject.objects.all().order_by('name')
    data = [{
        'id': subject.id,
        'name': subject.name
    } for subject in subjects]
    return JsonResponse(data, safe=False)

def api_teachers(request):
    teachers = Teacher.objects.all()
    subject_id = request.GET.get('subject_id')
    if subject_id:
        teachers = teachers.filter(subject_id=subject_id)
    
    data = [{
        'id': teacher.id,
        'name': teacher.full_name,
        'subject': teacher.subject.name
    } for teacher in teachers]
    return JsonResponse(data, safe=False)

def api_students(request):
    students = Student.objects.all()
    query = request.GET.get('q')
    if query:
        students = students.filter(
            full_name__icontains=query
        )
    
    data = [{
        'id': student.id,
        'name': student.full_name,
        'academic_level': student.academic_level.name
    } for student in students]
    return JsonResponse(data, safe=False)

def api_groups(request):
    groups = Group.objects.all()
    
    data = [{
        'id': group.id,
        'name': group.name,
        'subject': group.subject.name,
        'teacher': group.teacher.full_name,
        'student_count': group.students.count()
    } for group in groups]
    return JsonResponse(data, safe=False)

def api_sessions(request):
    sessions = Session.objects.all()
    group_id = request.GET.get('group_id')
    if group_id:
        sessions = sessions.filter(group_id=group_id)
    
    data = [{
        'id': session.id,
        'group': session.group.name,
        'date': session.date.strftime('%Y-%m-%d'),
        'start_time': session.start_time.strftime('%H:%M'),
        'duration': float(session.duration)
    } for session in sessions]
    return JsonResponse(data, safe=False)

def api_get_session_attendance(request, session_id):
    session = get_object_or_404(Session.objects.select_related('group'), id=session_id)
    group_students = session.group.students.all().order_by('full_name')

    # Get all attendance records for this session in one query
    session_attendance_records = Attendance.objects.filter(session=session).select_related('student')
    attendance_map = {record.student_id: record for record in session_attendance_records}

    data = []
    for student in group_students:
        record = attendance_map.get(student.id)

        status_data = {
            'student_id': student.id,
            'full_name': student.full_name,
            'paid': False,
            'present': False,
            'excused_absence': False,
            'attendance_time': None,
            'status': 'absent' # Default status if a record exists but isn't 'present'
        }

        if record:
            status_data.update({
                'paid': record.student_paid_for_session,
                'present': record.present,
                'excused_absence': record.excused_absence,
                'attendance_time': record.created_at.strftime("%Y-%m-%d %H:%M:%S") if record.created_at else None,
                'status': 'present' if record.present else ('excused' if record.excused_absence else 'absent')
            })

        data.append(status_data)

    return JsonResponse({'session_id': session_id, 'attendance': data})

from django.views.decorators.http import require_POST

@csrf_exempt # Using csrf_exempt for simplicity as client-side is expected to handle CSRF for fetch if needed, or for API token style auth.
@require_POST # Ensures this view only accepts POST requests.
def api_mark_all_absent(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    # Ensure the group is fetched correctly via the session
    if not session.group:
        return JsonResponse({'status': 'error', 'message': 'Session is not associated with a group.'}, status=400)

    group_student_ids = set(session.group.students.values_list('id', flat=True))
    attended_student_ids = set(Attendance.objects.filter(session=session).values_list('student_id', flat=True))

    students_to_mark_absent_ids = group_student_ids - attended_student_ids

    absent_records = []
    if students_to_mark_absent_ids:
        for student_id in students_to_mark_absent_ids:
            absent_records.append(Attendance(
                student_id=student_id,
                session=session,
                present=False,
                student_paid_for_session=False, # Default, can be changed later
                excused_absence=False
            ))
        if absent_records:
            Attendance.objects.bulk_create(absent_records)
            # log_action('bulk_absent_marked', f"Session {session_id}", f"{len(absent_records)} students marked absent.")

    count = len(absent_records)
    return JsonResponse({'status': 'success', 'message': f'تم تسجيل غياب لـ {count} طالب/طلاب بنجاح.', 'absent_count': count})

def api_get_group_students(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    students = group.students.all().order_by('full_name') #.select_related('academic_level') might be useful later

    student_data_list = []
    for s in students:
        student_data_list.append({
            'id': s.id,
            'full_name': s.full_name,
            # 'academic_level_name': s.academic_level.name if s.academic_level else None # Example for later
        })

    return JsonResponse({'group_id': group_id, 'group_name': group.name, 'students': student_data_list})

from django.views.decorators.csrf import csrf_exempt
import json
from django.views.decorators.http import require_POST
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import base64
import qrcode

@require_POST
def mark_absence_excused(request, student_id, attendance_id):
    student = get_object_or_404(Student, id=student_id)
    # Eagerly load related objects to prevent extra DB queries
    attendance = get_object_or_404(
        Attendance.objects.select_related('session__group'),
        id=attendance_id,
        student=student
    )

    if not attendance.present:
        with transaction.atomic():
            was_paid = attendance.student_paid_for_session

            # Always mark as excused
            attendance.excused_absence = True

            # If it was paid, refund the student and mark as unpaid
            if was_paid:
                group = attendance.session.group
                if group.price_per_4_sessions and group.price_per_4_sessions > Decimal('0'):
                    price_per_session = group.price_per_4_sessions / Decimal('4')
                    student.prepaid_balance += price_per_session
                    student.save()

                    attendance.student_paid_for_session = False
                    messages.success(request, f"تم تسجيل غياب حصة {attendance.session.date.strftime('%Y-%m-%d')} كغياب معذور، وتمت إعادة مبلغ الحصة إلى رصيد الطالب.")
                else:
                    messages.info(request, f"تم تسجيل غياب حصة {attendance.session.date.strftime('%Y-%m-%d')} كغياب معذور (لم يتم استرداد أي مبلغ لأن سعر الحصة هو صفر).")
            else:
                messages.success(request, f"تم تسجيل غياب حصة {attendance.session.date.strftime('%Y-%m-%d')} كغياب معذور.")

            attendance.save()
    else:
        messages.warning(request, "لا يمكن تسجيل غياب معذور لحصة كان الطالب فيها حاضراً.")

    return redirect('student_detail', student_id=student.id)


@csrf_exempt # Consider CSRF implications if this API were public; for internal use with JS fetch, this is simpler if client sends CSRF via header or if it's an API token auth.
def api_cancel_attendance(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method. Only POST is allowed.'}, status=405)

    try:
        # Assuming data is sent as JSON
        data = json.loads(request.body)
        session_id = data.get('session_id')
        student_id = data.get('student_id')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'}, status=400)

    if not session_id or not student_id:
        return JsonResponse({'status': 'error', 'message': 'Session ID and Student ID are required.'}, status=400)

    try:
        attendance_record = get_object_or_404(Attendance, session_id=session_id, student_id=student_id)
        # You might want to log this action before deleting
        # log_action('attendance_cancelled', f"Student {student_id} for session {session_id}", f"Cancelled by {request.user}")
        attendance_record.delete()
        return JsonResponse({'status': 'success', 'message': 'تم إلغاء الحضور بنجاح.'})
    except Attendance.DoesNotExist: # This case is handled by get_object_or_404, but explicit catch is fine too
        return JsonResponse({'status': 'error', 'message': 'سجل الحضور المحدد غير موجود.'}, status=404)
    except Exception as e:
        # Log the exception e for server-side debugging
        logger.error(f"Error cancelling attendance for session {session_id}, student {student_id}: {e}")
        return JsonResponse({'status': 'error', 'message': f'حدث خطأ غير متوقع: {str(e)}'}, status=500)

@csrf_exempt
@require_POST
def api_record_bulk_attendance(request):
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        session_ids = data.get('session_ids')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'بيانات JSON غير صالحة.'}, status=400)

    if not student_id or not session_ids or not isinstance(session_ids, list):
        return JsonResponse({'status': 'error', 'message': 'معرف الطالب وقائمة بمعرفات الحصص مطلوبان.'}, status=400)

    try:
        student = Student.objects.get(id=student_id)
        sessions = Session.objects.filter(id__in=session_ids)

        if len(session_ids) != sessions.count():
             return JsonResponse({'status': 'error', 'message': 'تم العثور على معرفات حصص غير صالحة.'}, status=400)

        created_count = 0
        already_exist_count = 0
        for session in sessions:
            _, created = Attendance.objects.get_or_create(
                student=student,
                session=session,
                defaults={'present': True, 'student_paid_for_session': False}
            )
            if created:
                created_count += 1
            else:
                already_exist_count += 1

        message = f"تم تسجيل حضور {created_count} حصص بنجاح."
        if already_exist_count > 0:
            message += f" {already_exist_count} حصص كانت مسجلة بالفعل."

        return JsonResponse({'status': 'success', 'message': message})

    except Student.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'الطالب غير موجود.'}, status=404)
    except Exception as e:
        logger.error(f"Error in bulk attendance recording: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'حدث خطأ غير متوقع.'}, status=500)


@csrf_exempt
@require_POST
def api_record_attendance_by_student(request):
    try:
        data = json.loads(request.body)
        student_identifier = data.get('student_identifier')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'بيانات JSON غير صالحة.'}, status=400)

    if not student_identifier:
        return JsonResponse({'status': 'error', 'message': 'معرف الطالب مطلوب.'}, status=400)

    # Find the student by ID or Card Number
    student = None
    if isinstance(student_identifier, int) or (isinstance(student_identifier, str) and student_identifier.isdigit()):
        try:
            student = Student.objects.get(pk=int(student_identifier))
        except Student.DoesNotExist:
            pass

    if not student and isinstance(student_identifier, str):
        try:
            student = Student.objects.get(card_number=student_identifier)
        except Student.DoesNotExist:
            pass
    elif not student and isinstance(student_identifier, int):
        try:
            student = Student.objects.get(card_number=str(student_identifier))
        except Student.DoesNotExist:
            pass

    if not student:
        return JsonResponse({'status': 'error', 'message': 'الطالب غير موجود.'}, status=404)

    # Find the nearest session for the student within the time window
    now = timezone.now()
    time_window_start = now - timedelta(hours=2)
    time_window_end = now + timedelta(hours=2)

    student_groups = student.group_set.all()
    if not student_groups.exists():
        return JsonResponse({'status': 'error', 'message': 'هذا الطالب غير مسجل في أي فوج.'}, status=404)

    potential_sessions = []
    for group in student_groups:
        sessions_in_group = Session.objects.filter(group=group, date=now.date())
        for session in sessions_in_group:
            session_start_dt = timezone.make_aware(datetime.datetime.combine(session.date, session.start_time))
            if time_window_start <= session_start_dt <= time_window_end:
                time_diff = abs(session_start_dt - now)
                potential_sessions.append((time_diff, session))

    if not potential_sessions:
        return JsonResponse({'status': 'error', 'message': 'لا توجد حصة نشطة لهذا الطالب في الوقت الحالي.'}, status=404)

    # If there are multiple potential sessions, return them for user selection
    if len(potential_sessions) > 1:
        sessions_data = []
        for time_diff, session in potential_sessions:
            sessions_data.append({
                'id': session.id,
                'group_name': session.group.name,
                'subject_name': session.group.subject.name,
                'date': session.date.strftime('%Y-%m-%d'),
                'start_time': session.start_time.strftime('%H:%M'),
            })
        return JsonResponse({
            'status': 'multiple_sessions_found',
            'message': 'تم العثور على عدة حصص. يرجى اختيار الحصة المطلوبة.',
            'sessions': sessions_data,
            'student_id': student.id
        })

    # If only one session is found, proceed to register attendance automatically
    target_session = potential_sessions[0][1]

    try:
        attendance, created = Attendance.objects.get_or_create(
            student=student,
            session=target_session
        )

        if not created and attendance.present:
            # The student was already marked as present, this is a true "already registered" case
            return JsonResponse({
                'status': 'already_registered',
                'message': f'الطالب {student.full_name} مسجل بالفعل في هذه الحصة.',
                'student_name': student.full_name,
                'session_info': f'{target_session.group.name} - {target_session.date}'
            }, status=200)

        # If the record was newly created OR if it existed but the student was marked absent,
        # we now mark them as present.
        attendance.present = True

        # --- Payment Logic ---
        payment_status_message = "الحصة غير مدفوعة" # Default message
        group = target_session.group
        price_per_session = Decimal('0.00')

        if group.price_per_4_sessions and group.price_per_4_sessions > 0:
            price_per_session = group.price_per_4_sessions / Decimal('4.0')

        if price_per_session > 0:
            # Check if student has enough balance and session is not already paid
            if not attendance.student_paid_for_session and student.prepaid_balance >= price_per_session:
                student.prepaid_balance -= price_per_session
                attendance.student_paid_for_session = True
                student.save(update_fields=['prepaid_balance'])
                payment_status_message = f"تم الدفع من الرصيد المسبق. الرصيد المتبقي: {student.prepaid_balance.quantize(Decimal('0.01'))} دج"
            elif attendance.student_paid_for_session:
                payment_status_message = "الحصة مدفوعة بالفعل"
            else: # Not enough balance
                payment_status_message = f"رصيد غير كافٍ. الرصيد الحالي: {student.prepaid_balance.quantize(Decimal('0.01'))} دج"
        elif attendance.student_paid_for_session:
             payment_status_message = "الحصة مدفوعة بالفعل"
        else: # Price is zero
             payment_status_message = "الحصة مجانية (السعر 0)"


        attendance.save()

        auto_excused_message = ""
        # Rule 2: If this is the student's first-ever 'present' record in this group, excuse previous absences.
        if Attendance.objects.filter(student=student, session__group=target_session.group, present=True).count() == 1:
            previous_absences_to_excuse = Attendance.objects.filter(
                student=student,
                session__group=target_session.group,
                session__date__lt=target_session.date,
                present=False,
                excused_absence=False
            )
            updated_count = previous_absences_to_excuse.update(excused_absence=True)
            if updated_count > 0:
                auto_excused_message = f"تم تحويل {updated_count} غياب سابق إلى غياب معذور تلقائياً."


        # Calculate unpaid sessions for the student in this group
        try:
            student_group = StudentGroup.objects.get(student=student, group=target_session.group)
            enrollment_date = student_group.enrollment_date
        except StudentGroup.DoesNotExist:
            enrollment_date = None

        unpaid_sessions_count = 0
        if enrollment_date:
            unpaid_sessions_count = Attendance.objects.filter(
                student=student,
                session__group=target_session.group,
                session__date__gte=enrollment_date,
                student_paid_for_session=False,
                excused_absence=False
            ).count()



        return JsonResponse({
            'status': 'success',
            'message': 'تم تسجيل الحضور بنجاح.',
            'student_name': student.full_name,
            'session_info': f'{target_session.group.name} - {target_session.date}',
            'payment_status_message': payment_status_message,
            'session_id': target_session.id,
            'unpaid_sessions_count': unpaid_sessions_count,
            'auto_excused_message': auto_excused_message
        }, status=201)

    except Exception as e:
        logger.error(f"Error creating or updating attendance for student {student.id} in session {target_session.id}: {e}")
        return JsonResponse({'status': 'error', 'message': 'حدث خطأ أثناء تسجيل الحضور.'}, status=500)


# Student Monthly Payment View
def student_monthly_payment_view(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    enrolled_groups = student.group_set.all().select_related('subject', 'teacher')
    selected_group_id = request.GET.get('group_id')

    group_details = None
    sessions_display = []
    # amount_due = Decimal('0.00') # Will be net_amount_due
    gross_amount_due = Decimal('0.00')
    net_amount_due = Decimal('0.00')
    price_per_session = Decimal('0.00')
    attended_but_not_paid_sessions_count = 0
    prepaid_sessions_count = 0
    student_prepaid_balance = student.prepaid_balance # Explicitly for context

    page_title = f"الدفع الشهري للطالب: {student.full_name}"

    if selected_group_id:
        try:
            selected_group = get_object_or_404(Group, id=selected_group_id, students=student)
            group_details = selected_group

            if selected_group.price_per_4_sessions > 0:
                price_per_session = selected_group.price_per_4_sessions / Decimal('4')

            try:
                student_group = StudentGroup.objects.get(student=student, group=selected_group)
                enrollment_date = student_group.enrollment_date
            except StudentGroup.DoesNotExist:
                enrollment_date = None

            all_student_sessions_for_group = Session.objects.filter(
                group=selected_group,
                date__lte=timezone.now().date()
            ).order_by('-date', '-start_time')

            if enrollment_date:
                all_student_sessions_for_group = all_student_sessions_for_group.filter(date__gte=enrollment_date)

            # The following loop for sessions_display will now use the potentially filtered all_student_sessions_for_group

            # unpaid_sessions_count = 0 # This counter is not used for gross_amount_due, removing from display loop.
            for session_obj_loop in all_student_sessions_for_group: # Iterate over filtered sessions. Limit for display if too many.
                 # For display purposes, maybe limit the number of sessions shown or paginate them if the list becomes very long.
                 # For now, we are showing all "relevant" sessions as per previous logic.
                # Fetch or create attendance record
                attendance, created = Attendance.objects.get_or_create(
                    student=student,
                    session=session_obj_loop,
                    defaults={'present': False, 'student_paid_for_session': False, 'excused_absence': False}
                )

                is_relevant = not attendance.student_paid_for_session or \
                              (not attendance.present and not attendance.excused_absence)

                if is_relevant:
                    status = "لم يحضر"
                    paid_status = "غير مدفوعة"
                    is_paid = False
                    excused = False

                    if attendance.present:
                        status = "حاضر"
                    elif attendance.excused_absence:
                        status = "غياب معذور"
                        excused = True
                    else: # Not present and not excused = غائب
                        status = "غائب"

                    if attendance.student_paid_for_session:
                        paid_status = "مدفوعة"
                        is_paid = True

                    can_be_excused = (
                        not attendance.present and
                        not attendance.excused_absence and
                        not attendance.student_paid_for_session and
                        session_obj_loop.date < timezone.now().date()
                    )

                    sessions_display.append({
                        'session_id': session_obj_loop.id,
                        'date': session_obj_loop.date,
                        'time': session_obj_loop.start_time,
                        'status': status,
                        'paid_status': paid_status,
                        'is_paid': is_paid,
                        'is_excused': excused,
                        'can_be_excused': can_be_excused
                    })

            # Calculate amount due based on unpaid, non-excused sessions
            # This is a simplified calculation. True accounting might be more complex.
            # For now, count unpaid sessions that are not excused absences.

            # Recalculate unpaid_sessions_count for amount_due accurately
            # This should count sessions that require payment.
            billable_unpaid_count = 0
            # Also calculate attended_but_not_paid_sessions_count in the same loop

            # Base query for chronological sessions
            all_sessions_for_group_chronological = Session.objects.filter(
                group=selected_group
            ).order_by('date', 'start_time')

            if enrollment_date:
                all_sessions_for_group_chronological = all_sessions_for_group_chronological.filter(date__gte=enrollment_date)

            current_date = timezone.now().date()

            for session_obj in all_sessions_for_group_chronological:
                att = Attendance.objects.filter(student=student, session=session_obj).first()
                is_past_or_current_session = session_obj.date <= current_date

                if att:
                    if not att.student_paid_for_session and not att.excused_absence:
                        if is_past_or_current_session: # Only count past/current sessions as billable
                            billable_unpaid_count += 1
                        # For attended_but_not_paid, session date doesn't strictly matter as long as attendance exists
                        if att.present:
                             attended_but_not_paid_sessions_count += 1
                else: # No attendance record
                    if is_past_or_current_session: # Billable if past/current and no record
                         billable_unpaid_count +=1
                         # Not attended if no record, so doesn't contribute to attended_but_not_paid_sessions_count

            gross_amount_due = billable_unpaid_count * price_per_session
            net_amount_due = gross_amount_due - student_prepaid_balance # Use the explicit variable
            if net_amount_due < Decimal('0.00'):
                net_amount_due = Decimal('0.00')

            # Calculate prepaid_sessions_count
            if price_per_session > Decimal('0.00') and student_prepaid_balance > Decimal('0.00'):
                import math # Ensure math is imported
                prepaid_sessions_count = math.floor(student_prepaid_balance / price_per_session)
            else:
                prepaid_sessions_count = 0

        except Group.DoesNotExist:
            messages.error(request, "الفوج المحدد غير صحيح أو الطالب غير مسجل فيه.")
            group_details = None # Ensure it's reset

    if request.method == 'POST':
        action = request.POST.get('action')
        group_id_post = request.POST.get('group_id') # This is from a hidden input in the form

        # Initialize group_details and price_per_session for POST context
        current_group_details_post = None
        current_price_per_session_post = Decimal('0.00')

        if group_id_post:
            try:
                current_group_details_post = get_object_or_404(Group, id=group_id_post, students=student)
                if current_group_details_post.price_per_4_sessions > 0:
                    current_price_per_session_post = current_group_details_post.price_per_4_sessions / Decimal('4')
            except Group.DoesNotExist:
                messages.error(request, "الفوج المحدد في الطلب غير صالح أو الطالب ليس مسجلاً فيه.")
                return redirect(reverse('student_monthly_payment', args=[student_id]))

        if not current_group_details_post:
            messages.error(request, "لم يتم تحديد فوج صالح للعملية المطلوبة.")
            return redirect(reverse('student_monthly_payment', args=[student_id]))

        # Now use current_group_details_post and current_price_per_session_post for POST actions

        if action == 'mark_excused':
            session_id_to_excuse = request.POST.get('session_id')
            if session_id_to_excuse:
                try:
                    attendance_to_excuse = Attendance.objects.select_related('session__group').get(session_id=session_id_to_excuse, student=student)

                    # Ensure the session belongs to the group being viewed to calculate price correctly
                    if attendance_to_excuse.session.group.id != current_group_details_post.id:
                        messages.error(request, "خطأ: الحصة لا تنتمي إلى الفوج المحدد.")
                        return redirect(reverse('student_monthly_payment', args=[student_id]) + f'?group_id={group_id_post}')

                    if not attendance_to_excuse.present:
                        # Start a database transaction to ensure all or nothing is saved.
                        with transaction.atomic():
                            was_paid = attendance_to_excuse.student_paid_for_session

                            # Always mark as excused
                            attendance_to_excuse.excused_absence = True

                            # If it was paid, refund the student and mark as unpaid
                            if was_paid:
                                if current_price_per_session_post > Decimal('0'):
                                    student.prepaid_balance += current_price_per_session_post
                                    student.save()

                                    attendance_to_excuse.student_paid_for_session = False

                                    messages.success(request, f"تم تسجيل غياب حصة {attendance_to_excuse.session.date.strftime('%Y-%m-%d')} كغياب معذور، وتمت إعادة مبلغ الحصة إلى رصيد الطالب.")
                                else:
                                    # This case handles if the session price is zero, still mark as excused
                                    messages.info(request, f"تم تسجيل غياب حصة {attendance_to_excuse.session.date.strftime('%Y-%m-%d')} كغياب معذور (لم يتم استرداد أي مبلغ لأن سعر الحصة هو صفر).")
                            else:
                                # If it wasn't paid, just mark it as excused
                                messages.success(request, f"تم تسجيل غياب حصة {attendance_to_excuse.session.date.strftime('%Y-%m-%d')} كغياب معذور.")

                            attendance_to_excuse.save()

                    else:
                        messages.warning(request, "لا يمكن تسجيل غياب معذور لحصة كان الطالب فيها حاضراً.")
                except Attendance.DoesNotExist:
                    messages.error(request, "سجل الحضور المحدد غير موجود.")
            return redirect(reverse('student_monthly_payment', args=[student_id]) + f'?group_id={group_id_post}')

        elif action == 'process_payment':
            amount_paid_str = request.POST.get('amount_paid')
            try:
                amount_paid_from_form = Decimal(amount_paid_str) # Renamed to avoid conflict
                amount_paid = amount_paid_from_form # Effective amount to be used for payment processing

                prepaid_used_this_transaction = Decimal('0.00')
                if student.prepaid_balance > Decimal('0.00'):
                    if student.prepaid_balance >= amount_paid_from_form : # Prepaid covers all or more than the form amount
                        # This interpretation is tricky. If form amount is what they INTEND to pay now,
                        # and prepaid is enough, then form amount is covered by prepaid.
                        # OR if amount_paid_from_form is the TOTAL they want to settle, including using prepaid.
                        # Assuming amount_paid_from_form is the cash/card payment being made NOW.
                        # The prepaid will be added to this.
                        messages.info(request, f"تم استخدام رصيد مدفوع مقدماً بقيمة: {student.prepaid_balance} دج.")
                        amount_paid += student.prepaid_balance
                        prepaid_used_this_transaction = student.prepaid_balance
                        student.prepaid_balance = Decimal('0.00')
                        # student.save() # Save student after prepaid is fully used or partially used.
                    else: # Prepaid covers some part of what might be due, or just adds to the payment
                        messages.info(request, f"تم استخدام رصيد مدفوع مقدماً بقيمة: {student.prepaid_balance} دج.")
                        amount_paid += student.prepaid_balance
                        prepaid_used_this_transaction = student.prepaid_balance
                        student.prepaid_balance = Decimal('0.00')
                        # student.save()

                if amount_paid <= 0: # Check effective amount_paid
                    messages.error(request, "المبلغ المدفوع (بعد إضافة الرصيد المسبق إن وجد) يجب أن يكون أكبر من صفر.")
                else:
                    # Logic for processing payment
                    # 1. Identify billable (unpaid, non-excused) sessions chronologically
                    sessions_to_pay_for = []
                    # Use the correctly fetched group details for POST
                    all_sessions_chronological = Session.objects.filter(group=current_group_details_post).order_by('date', 'start_time')

                    current_balance = amount_paid # Amount available to pay off sessions (includes prepaid if used)
                    sessions_paid_in_this_transaction_count = 0
                    list_of_session_ids_just_paid = [] # Initialize list to store IDs of paid sessions
                    successfully_paid_session_dates = [] # For consolidated messaging

                    for session_obj in all_sessions_chronological:
                        if current_balance <= Decimal('0'): # Stop if no balance left
                            break

                        # Ensure price_per_session (current_price_per_session_post) is valid before proceeding
                        if current_price_per_session_post <= Decimal('0'):
                            messages.error(request, "سعر الحصة المحدد للفوج غير صالح. لا يمكن معالجة الدفع.")
                            current_balance = Decimal('-1') # Mark balance as invalid to stop further processing
                            break

                        attendance, created = Attendance.objects.get_or_create(
                            student=student,
                            session=session_obj,
                            defaults={'present': False, 'student_paid_for_session': False, 'excused_absence': False}
                        )

                        if not attendance.student_paid_for_session and not attendance.excused_absence:
                            if current_balance >= current_price_per_session_post:
                                attendance.student_paid_for_session = True
                                attendance.save()
                                current_balance -= current_price_per_session_post
                                sessions_paid_in_this_transaction_count += 1
                                list_of_session_ids_just_paid.append(str(session_obj.id)) # Add ID to list
                                successfully_paid_session_dates.append(session_obj.date.strftime('%Y-%m-%d'))
                                # messages.success(request, f"تم دفع حصة {session_obj.date.strftime('%Y-%m-%d')} بنجاح.") # Removed for consolidation
                            else:
                                # Not enough balance to cover this session fully
                                if sessions_paid_in_this_transaction_count == 0 and not successfully_paid_session_dates: # If no session was paid at all with the amount
                                     messages.info(request, f"المبلغ المدفوع {amount_paid_from_form} غير كافٍ لدفع حصة كاملة بسعر {current_price_per_session_post}.") # Use amount_paid_from_form for clarity
                                break # Stop processing further sessions if balance can't cover the current one

                    # Overpayment logic - this loop structure might be redundant if the first loop already processes all available balance.
                    # However, if the first loop breaks due to not enough for *one* session, but there's still *some* balance,
                    # this second loop ensures that balance is handled (e.g. added to prepaid).
                    # The original logic for `additional_sessions_paid_with_overpayment` implies it was intended to pay more sessions.
                    # For now, let's refine the message part and assume the loop logic for paying is okay.
                    # The `list_of_session_ids_just_paid` already collects all paid sessions from both loops.

                    # Consolidate messages for successfully paid sessions
                    if successfully_paid_session_dates:
                        messages.success(request, f"تم دفع {len(successfully_paid_session_dates)} حصص بنجاح للتواريخ: {', '.join(sorted(list(set(successfully_paid_session_dates))))}.")

                    # Handle remaining balance and other info messages
                    # The `additional_sessions_paid_with_overpayment` was based on a second loop.
                    # Given `list_of_session_ids_just_paid` now includes all, we can compare its length to `sessions_paid_in_this_transaction_count`
                    # This part needs careful review to ensure messages align with the unified collection of paid sessions.

                    # Let's simplify: if current_balance remains after attempting all payments.
                    if current_balance > Decimal('0.00') and current_price_per_session_post > Decimal('0.00'):
                        # This means there's leftover money.
                        # If some sessions were paid initially, this is true overpayment.
                        # If NO sessions were paid initially (e.g., all were already paid, or amount was too small for any single session),
                        # then the entire `amount_paid` (adjusted by prepaid) might become `current_balance`.

                        student.prepaid_balance += current_balance
                        messages.success(request, f"تم إضافة المبلغ المتبقي {current_balance.quantize(Decimal('0.01'))} دج إلى الرصيد المدفوع مقدماً للطالب.")

                    elif sessions_paid_in_this_transaction_count == 0 and not successfully_paid_session_dates and amount_paid > Decimal('0.00') and current_price_per_session_post > Decimal('0.00'):
                        # This case: amount_paid (cash + initial prepaid) was positive, but no sessions were paid (e.g., all already paid or amount too small for any).
                        # The remaining current_balance (which is amount_paid here) should go to prepaid.
                        # This condition might be partly covered by the one above if current_balance is the full amount_paid.
                        # To avoid double-adding to prepaid or conflicting messages, this needs to be clean.
                        # If `successfully_paid_session_dates` is empty, and `amount_paid` (cash+initial_prepaid) was > 0
                        if not student.prepaid_balance == (amount_paid - prepaid_used_this_transaction + current_balance): # Avoid double message if already handled by above
                             student.prepaid_balance += current_balance # This is the original amount_paid if nothing was spent
                             messages.info(request, f"لا توجد حصص لدفعها أو المبلغ غير كافٍ. تم إضافة {current_balance.quantize(Decimal('0.01'))} دج بالكامل إلى الرصيد المدفوع مقدماً.")

                    # Save student if prepaid_balance was potentially changed
                    # This includes: initial use of prepaid, or adding remaining balance to prepaid.
                    if prepaid_used_this_transaction > Decimal('0.00') or (current_balance > Decimal('0.00') and current_price_per_session_post > Decimal('0.00')) :
                        student.save()

                    # Always try to generate a receipt URL if a payment was attempted
                    if amount_paid_from_form > Decimal('0.00') or prepaid_used_this_transaction > Decimal('0.00'):
                        paid_session_ids_str = ",".join(list_of_session_ids_just_paid)
                        receipt_url = reverse('print_student_payment_receipt', args=[student_id, current_group_details_post.id]) + f"?amount_paid={amount_paid_from_form}&session_ids={paid_session_ids_str}&prepaid_used={prepaid_used_this_transaction}"
                        request.session['last_payment_receipt_url'] = receipt_url
                    # The condition for amount_paid <= 0 (effective) is handled by the error message earlier.

            except ValueError: # Catches Decimal conversion error for amount_paid_str
                messages.error(request, "المبلغ المدفوع المدخل غير صالح.")

            # Preserve the group_id in the redirect URL
            redirect_url = reverse('student_monthly_payment', args=[student_id])
            if group_id_post:
                redirect_url += f'?group_id={group_id_post}'
            return redirect(redirect_url)

        elif action == 'reduce_prepaid_balance':
            sessions_to_reduce_count_str = request.POST.get('sessions_to_reduce_count')
            group_id_for_reduction_price = request.POST.get('group_id') # This is selected_group.id from the form

            try:
                sessions_to_reduce_count = int(sessions_to_reduce_count_str)
                if sessions_to_reduce_count <= 0:
                    messages.error(request, "عدد الحصص للتخفيض يجب أن يكون رقماً موجباً.")
                    raise ValueError("Invalid session count")

                group_for_price_info = get_object_or_404(Group, id=group_id_for_reduction_price)

                price_per_session_for_reduction = Decimal('0.00')
                if group_for_price_info.price_per_4_sessions and group_for_price_info.price_per_4_sessions > Decimal('0'):
                    price_per_session_for_reduction = group_for_price_info.price_per_4_sessions / Decimal('4')

                if price_per_session_for_reduction <= Decimal('0.00'):
                    messages.error(request, "سعر الفوج المحدد غير صالح لحساب التخفيض (السعر صفر أو سالب).")
                    raise ValueError("Invalid group price for reduction")

                amount_to_deduct = sessions_to_reduce_count * price_per_session_for_reduction
                old_balance = student.prepaid_balance

                if student.prepaid_balance >= amount_to_deduct:
                    student.prepaid_balance -= amount_to_deduct
                    student.save()
                    log_action(
                        'prepaid_balance_reduced',
                        f"Student {student.id} - {student.full_name}",
                        f"Reduced by {amount_to_deduct} DZD ({sessions_to_reduce_count} sessions from group {group_for_price_info.name}). Old balance: {old_balance}, New balance: {student.prepaid_balance}"
                    )
                    messages.success(request, f"تم تخفيض الرصيد المسبق بنجاح بمقدار {amount_to_deduct} دج.")
                else:
                    messages.error(request, f"لا يمكن تخفيض الرصيد. الرصيد الحالي ({student.prepaid_balance} دج) أقل من المبلغ المراد خصمه ({amount_to_deduct} دج).")

            except (ValueError, TypeError): # Catches int conversion error and raised ValueErrors
                if not messages.get_messages(request): # Add a generic error if none was added yet
                    messages.error(request, "الرجاء إدخال عدد حصص صحيح للتخفيض.")
            except Group.DoesNotExist:
                 messages.error(request, "الفوج المحدد لحساب سعر التخفيض غير موجود.")

            return redirect(reverse('student_monthly_payment', args=[student_id]) + f'?group_id={group_id_for_reduction_price}')


    receipt_url_from_session = request.session.pop('last_payment_receipt_url', None)
    context = {
        'student': student,
        'enrolled_groups': enrolled_groups,
        'selected_group': group_details,
        'sessions_display': sessions_display,
        'gross_amount_due': gross_amount_due,
        'net_amount_due': net_amount_due,
        'price_per_session': price_per_session,
        'student_prepaid_balance': student_prepaid_balance,
        'attended_but_not_paid_sessions_count': attended_but_not_paid_sessions_count,
        'prepaid_sessions_count': prepaid_sessions_count,
        'page_title': page_title,
        'receipt_url': receipt_url_from_session,
    }
    return render(request, 'school_app/student_monthly_payment.html', context)


def print_student_payment_receipt(request, student_id, group_id):
    student = get_object_or_404(Student, id=student_id)
    group = get_object_or_404(Group, id=group_id)
    amount_paid_str = request.GET.get('amount_paid', '0') # This is cash/card payment
    session_ids_str = request.GET.get('session_ids', '')
    prepaid_used_str = request.GET.get('prepaid_used', '0')


    try:
        amount_paid_cash_card = Decimal(amount_paid_str)
        prepaid_used = Decimal(prepaid_used_str)
    except ValueError:
        amount_paid_cash_card = Decimal('0.00')
        prepaid_used = Decimal('0.00')
        # messages.error(request, "بيانات الإيصال غير صالحة.") # Cannot send messages from here easily
        # return redirect(...) # Or handle error appropriately

    total_credited_for_sessions = amount_paid_cash_card + prepaid_used

    paid_sessions = []
    if session_ids_str:
        try:
            session_ids = [int(sid) for sid in session_ids_str.split(',') if sid.isdigit()]
            # Ensure sessions belong to the specified group for this student's receipt context
            paid_sessions = Session.objects.filter(id__in=session_ids, group=group).order_by('date', 'start_time')
        except ValueError:
            pass # Keep paid_sessions empty

    context = {
        'student': student,
        'group': group,
        'amount_paid_cash_card': amount_paid_cash_card, # Actual amount handed over
        'prepaid_used': prepaid_used, # Amount taken from prepaid balance
        'total_credited_for_sessions': total_credited_for_sessions, # Total value applied to sessions
        'paid_sessions': paid_sessions,
        'price_per_session': group.price_per_4_sessions / Decimal('4') if group.price_per_4_sessions and group.price_per_4_sessions > 0 else Decimal('0.00'),
        'print_date': timezone.now(),
    }
    return render(request, 'school_app/print_student_payment_receipt.html', context)


def print_teacher_payment_receipt(request, teacher_id, group_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    group = get_object_or_404(Group, id=group_id)

    # Retrieve details from GET parameters
    total_payment_amount_str = request.GET.get('amount_paid', '0')
    price_per_instance_str = request.GET.get('price_per_session', '0')
    total_presences_str = request.GET.get('total_presences', '0')
    total_absences_counted_str = request.GET.get('total_absences_counted', '0')
    student_count_str = request.GET.get('student_count', '0')
    total_sessions_str = request.GET.get('total_sessions', '0')
    excused_absences_count_str = request.GET.get('excused_absences_count', '0')

    try:
        total_payment_amount = Decimal(total_payment_amount_str)
        price_per_instance = Decimal(price_per_instance_str)
        total_presences = int(total_presences_str)
        total_absences_counted = int(total_absences_counted_str)
        student_count = int(student_count_str)
        total_sessions = int(total_sessions_str)
        excused_absences_count = int(excused_absences_count_str)
    except (ValueError, TypeError):
        messages.error(request, "بيانات الإيصال غير صالحة.")
        return redirect(reverse('teacher_monthly_payment', args=[teacher_id]) + f"?group_id={group_id}")

    context = {
        'teacher': teacher,
        'group': group,
        'total_payment_amount': total_payment_amount,
        'price_per_instance': price_per_instance,
        'total_presences': total_presences,
        'total_absences_counted': total_absences_counted,
        'student_count': student_count,
        'total_sessions': total_sessions,
        'excused_absences_count': excused_absences_count,
        'print_date': timezone.now(),
    }
    return render(request, 'school_app/print_teacher_payment_receipt.html', context)


def teacher_monthly_payment_view(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    taught_groups = Group.objects.filter(teacher=teacher).select_related('subject')

    # --- Context variables ---
    selected_group_id_str = request.GET.get('group_id') or request.POST.get('group_id_hidden')
    teacher_price_per_session_str = request.GET.get('teacher_price_per_session') or request.POST.get('teacher_price_per_session')

    group_details = None
    sessions_to_display = []
    calculated_payment_details = request.session.get('calculated_teacher_payment_details')
    page_title = f"الدفع الشهري للمدرس: {teacher.full_name}"

    # --- POST request handling ---
    if request.method == 'POST':
        action = request.POST.get('action')
        group_id_post = request.POST.get('group_id_hidden')

        if not group_id_post or not teacher_price_per_session_str:
            messages.error(request, "الرجاء اختيار فوج وإدخال سعر الحصة أولاً.")
            return redirect(reverse('teacher_monthly_payment', args=[teacher_id]))

        current_group_post = get_object_or_404(Group, id=group_id_post, teacher=teacher)
        redirect_url = reverse('teacher_monthly_payment', args=[teacher_id]) + f'?group_id={group_id_post}&teacher_price_per_session={teacher_price_per_session_str}'

        if action == 'calculate_payment':
            selected_session_ids = request.POST.getlist('sessions_to_pay_ids')
            if not selected_session_ids:
                messages.error(request, "الرجاء اختيار حصة واحدة على الأقل للحساب.")
                return render(request, 'school_app/teacher_monthly_payment.html', {
                    'teacher': teacher,
                    'taught_groups': taught_groups,
                    'selected_group': current_group_post,
                    'sessions_to_display': sessions_to_display,
                    'teacher_price_per_session_str': teacher_price_per_session_str,
                    'calculated_payment_details': calculated_payment_details,
                    'page_title': page_title,
                    'receipt_url': request.session.pop('last_teacher_payment_receipt_url', None)
                })

            # --- Simplified Calculation Logic ---
            attendance_records = Attendance.objects.filter(
                session_id__in=selected_session_ids,
                session__group=current_group_post
            )

            # Count students present + students with unexcused absences
            total_payable_instances = attendance_records.filter(
                Q(present=True) | Q(excused_absence=False)
            ).count()

            total_presences = attendance_records.filter(present=True).count()
            total_unexcused_absences = total_payable_instances - total_presences

            try:
                teacher_price_decimal = Decimal(teacher_price_per_session_str)
            except ValueError:
                messages.error(request, "سعر الحصة المدخل غير صالح.")
                return redirect(redirect_url)

            calculated_total_payment = total_payable_instances * teacher_price_decimal

            request.session['calculated_teacher_payment_details'] = {
                'group_id': current_group_post.id,
                'group_name': current_group_post.name,
                'teacher_price_per_session': str(teacher_price_decimal),
                'selected_session_ids': selected_session_ids,
                'total_presences': total_presences,
                'total_unexcused_absences_for_payment': total_unexcused_absences,
                'total_payable_instances': total_payable_instances,
                'calculated_total_payment': str(calculated_total_payment)
            }
            messages.success(request, "تم حساب المبلغ. يرجى المراجعة والتأكيد.")
            return redirect(redirect_url)

        elif action == 'process_payment':
            if not calculated_payment_details or str(calculated_payment_details.get('group_id')) != group_id_post:
                messages.error(request, "تفاصيل الدفع غير متطابقة أو مفقودة. يرجى إعادة الحساب.")
                if 'calculated_teacher_payment_details' in request.session:
                    del request.session['calculated_teacher_payment_details']
                return redirect(redirect_url)

            session_ids_to_mark = calculated_payment_details.get('selected_session_ids', [])
            teacher_price_decimal = Decimal(calculated_payment_details.get('teacher_price_per_session', '0'))

            final_payment_amount = Decimal('0.00')
            compensated_count = 0

            with transaction.atomic():
                sessions_to_process = Session.objects.filter(id__in=session_ids_to_mark, group=current_group_post)
                for session in sessions_to_process:
                    # Calculate payable instances for this specific session
                    payable_instances_count = Attendance.objects.filter(
                        session=session
                    ).filter(Q(present=True) | Q(excused_absence=False)).count()

                    session_payment_amount = payable_instances_count * teacher_price_decimal

                    session.teacher_payment_amount = session_payment_amount
                    session.teacher_compensated = True
                    session.save()

                    final_payment_amount += session_payment_amount
                    compensated_count += 1

            if compensated_count > 0:
                student_count = current_group_post.students.count()
                all_absences_in_sessions = Attendance.objects.filter(session_id__in=session_ids_to_mark, present=False)
                excused_absences_count = all_absences_in_sessions.filter(excused_absence=True).count()

                receipt_url = reverse('print_teacher_payment_receipt', args=[teacher.id, current_group_post.id]) + \
                              f"?amount_paid={final_payment_amount}" + \
                              f"&price_per_session={calculated_payment_details.get('teacher_price_per_session', 0)}" + \
                              f"&total_presences={calculated_payment_details.get('total_presences', 0)}" + \
                              f"&total_absences_counted={calculated_payment_details.get('total_unexcused_absences_for_payment', 0)}" + \
                              f"&student_count={student_count}" + \
                              f"&total_sessions={len(session_ids_to_mark)}" + \
                              f"&excused_absences_count={excused_absences_count}"
                request.session['last_teacher_payment_receipt_url'] = receipt_url
                messages.success(request, f"تم تسجيل دفع المستحقات لـ {compensated_count} حصة بنجاح.")
            else:
                messages.info(request, "لم يتم تحديث أي حصص. قد تكون دفعت مسبقاً.")

            del request.session['calculated_teacher_payment_details']
            return redirect(redirect_url)

        elif action == 'mark_student_absence_excused':
            attendance_id_to_excuse = request.POST.get('attendance_id')
            if not attendance_id_to_excuse:
                messages.error(request, "لم يتم تقديم معرف الحضور.")
                return redirect(redirect_url)

            try:
                # Use select_related to pre-fetch related objects in one go
                attendance = get_object_or_404(
                    Attendance.objects.select_related('student', 'session__group'),
                    id=attendance_id_to_excuse,
                    session__group=current_group_post
                )

                if attendance.present:
                    messages.warning(request, "لا يمكن عذر طالب حاضر.")
                else:
                    with transaction.atomic():
                        was_paid = attendance.student_paid_for_session
                        student_to_refund = attendance.student

                        # Always mark as excused
                        attendance.excused_absence = True

                        if was_paid:
                            group_price = attendance.session.group.price_per_4_sessions
                            if group_price and group_price > Decimal('0'):
                                price_per_session = group_price / Decimal('4')
                                student_to_refund.prepaid_balance += price_per_session
                                student_to_refund.save()

                                attendance.student_paid_for_session = False
                                messages.success(request, f"تم عذر غياب الطالب {attendance.student.full_name} وإعادة مبلغ {price_per_session} دج إلى رصيده.")
                            else:
                                messages.success(request, f"تم عذر غياب الطالب {attendance.student.full_name} بنجاح (لم يتم استرداد أي مبلغ لأن سعر الحصة هو صفر).")
                        else:
                            messages.success(request, f"تم عذر غياب الطالب {attendance.student.full_name} بنجاح.")

                        attendance.save()

                        # Invalidate any previous calculation since the number of payable instances might change
                        if 'calculated_teacher_payment_details' in request.session:
                            del request.session['calculated_teacher_payment_details']
                            messages.info(request, "تم إلغاء الحساب السابق، يرجى إعادة حساب المبلغ.")

            except Http404:
                messages.error(request, "لم يتم العثور على سجل الحضور المحدد.")

            return redirect(redirect_url)

    # --- GET request logic ---
    if selected_group_id_str:
        try:
            selected_group_id = int(selected_group_id_str)
            group_details = get_object_or_404(Group, id=selected_group_id, teacher=teacher)

            unpaid_sessions = Session.objects.filter(
                group=group_details,
                teacher_attended=True,
                teacher_compensated=False
            ).order_by('date', 'start_time').prefetch_related('group__students', 'attendance_set')

            for session in unpaid_sessions:
                student_statuses = []
                all_students_in_group = list(session.group.students.all())
                attendance_map = {att.student_id: att for att in session.attendance_set.all()}

                for student in all_students_in_group:
                    attendance = attendance_map.get(student.id)
                    if not attendance:
                        # Create missing attendance records on the fly if needed, but ideally they exist.
                        # For this view's purpose, we can assume they should exist. If not, treat as unexcused absent.
                        attendance, _ = Attendance.objects.get_or_create(
                            student=student, session=session,
                            defaults={'present': False, 'excused_absence': False}
                        )

                    student_statuses.append({
                        'name': student.full_name,
                        'attendance_id': attendance.id,
                        'is_present': attendance.present,
                        'is_excused': attendance.excused_absence
                    })

                if student_statuses:
                    sessions_to_display.append({
                        'session_id': session.id,
                        'date': session.date,
                        'time': session.start_time,
                        'student_statuses': sorted(student_statuses, key=lambda x: x['name'])
                    })
        except (ValueError, Group.DoesNotExist):
            messages.error(request, "الفوج المحدد غير صالح.")
            group_details = None

    context = {
        'teacher': teacher,
        'taught_groups': taught_groups,
        'selected_group': group_details,
        'sessions_to_display': sessions_to_display,
        'teacher_price_per_session_str': teacher_price_per_session_str,
        'calculated_payment_details': calculated_payment_details,
        'page_title': page_title,
        'receipt_url': request.session.pop('last_teacher_payment_receipt_url', None)
    }
    return render(request, 'school_app/teacher_monthly_payment.html', context)


def print_student_qr_code(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(student.card_number)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Write the QR code to an in-memory buffer
    buffer = BytesIO()
    img.save(buffer, format="PNG")

    # Encode the image buffer to a base64 string
    qr_code_image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    context = {
        'student': student,
        'qr_code_image_base64': qr_code_image_base64,
        'page_title': f"طباعة QR Code للطالب: {student.full_name}"
    }

    return render(request, 'school_app/print_student_qr_code.html', context)
