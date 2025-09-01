from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
import json

from .models import Student, Teacher, AcademicLevel, Subject, Group, Session, Attendance, ActionLog
from . import views # To access constants like REGISTRATION_FEE_AMOUNT

# A_REGISTRATION_FEE_AMOUNT = Decimal('500.00') # Defined in views

class BasicSetupTests(TestCase):
    def test_example(self):
        self.assertEqual(1 + 1, 2)

    def setUp(self):
        # Common setup for tests: Client, some basic data
        self.client = Client()

        # Academic Levels
        self.level_primary1 = AcademicLevel.objects.create(name="السنة الأولى ابتدائي", category="PRIMARY")
        self.level_middle1 = AcademicLevel.objects.create(name="السنة الأولى متوسط", category="MIDDLE")
        self.level_high1 = AcademicLevel.objects.create(name="السنة الأولى ثانوي", category="HIGH")

        # Subjects
        self.subject_math = Subject.objects.create(name="رياضيات")
        self.subject_arabic = Subject.objects.create(name="لغة عربية")

        # Teacher
        self.teacher1 = Teacher.objects.create(
            full_name="أستاذ قدير",
            phone_number="0555123123", subject=self.subject_math
        )

        # Student
        self.student1 = Student.objects.create(
            full_name="طالب مجتهد",
            phone_number="0777123123", guardian_phone="0666123123",
            birth_day=1, birth_month=1, birth_year=2005,
            academic_level=self.level_high1,
            registration_fee_paid=False # Initially not paid
        )
        self.student1.card_number = f"CARD-{self.student1.created_at.year}-{self.student1.id:05d}"
        self.student1.save()

        self.student2 = Student.objects.create(
            full_name="طالبة ذكية",
            phone_number="0777123124", guardian_phone="0666123124",
            birth_day=5, birth_month=5, birth_year=2006,
            academic_level=self.level_middle1,
            registration_fee_paid=True
        )
        self.student2.card_number = f"CARD-{self.student2.created_at.year}-{self.student2.id:05d}"
        self.student2.save()

        # Group
        self.group1 = Group.objects.create(
            name="فوج الرياضيات ثانوي", subject=self.subject_math, teacher=self.teacher1,
            price_per_4_sessions=Decimal('2000.00'), # 500 per session
            session_day=0, session_start_time="14:00:00", session_duration=Decimal('1.5')
        )
        self.group1.academic_levels.add(self.level_high1)
        self.group1.students.add(self.student1)

        # Sessions for Group1
        self.session1_g1 = Session.objects.create(
            group=self.group1, date=timezone.now().date() - timezone.timedelta(days=14),
            start_time="14:00:00", duration=Decimal('1.5'), teacher_attended=True
        )
        self.session2_g1 = Session.objects.create(
            group=self.group1, date=timezone.now().date() - timezone.timedelta(days=7),
            start_time="14:00:00", duration=Decimal('1.5'), teacher_attended=True
        )
        self.session3_g1 = Session.objects.create( # Current week's session
            group=self.group1, date=timezone.now().date(),
            start_time="14:00:00", duration=Decimal('1.5'), teacher_attended=True
        )
        self.session4_g1 = Session.objects.create( # Future session
            group=self.group1, date=timezone.now().date() + timezone.timedelta(days=7),
            start_time="14:00:00", duration=Decimal('1.5') # Teacher attendance not yet set
        )

        # Attendance records for student1 in group1
        # Session 1: Present, Paid
        Attendance.objects.create(student=self.student1, session=self.session1_g1, present=True, student_paid_for_session=True)
        # Session 2: Absent, Not Paid
        Attendance.objects.create(student=self.student1, session=self.session2_g1, present=False, student_paid_for_session=False)
        # Session 3: Present, Not Paid (yet)
        Attendance.objects.create(student=self.student1, session=self.session3_g1, present=True, student_paid_for_session=False)


class RegistrationFeeTests(BasicSetupTests):
    def test_registration_fee_constant_value(self):
        # Test the constant value directly from views module
        self.assertEqual(views.REGISTRATION_FEE_AMOUNT, Decimal('500.00'))

    def test_registration_fee_in_student_payment_context(self):
        # Test if the correct fee is passed to student_payment template
        self.client.force_login(User.objects.create_user('testuser')) # Assuming login is required
        response = self.client.get(reverse('student_payment', args=[self.student1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('REGISTRATION_FEE_AMOUNT', response.context)
        self.assertEqual(response.context['REGISTRATION_FEE_AMOUNT'], Decimal('500.00'))

        # Test fee display in print_registration_confirmation
        # First, mark fee as paid to allow access to print confirmation
        self.student1.registration_fee_paid = True
        self.student1.save()
        response_print = self.client.get(reverse('print_registration_confirmation', args=[self.student1.id]))
        self.assertEqual(response_print.status_code, 200)
        self.assertIn('REGISTRATION_FEE_AMOUNT', response_print.context)
        self.assertEqual(response_print.context['REGISTRATION_FEE_AMOUNT'], Decimal('500.00'))

# Dummy User model for force_login if not using custom user model that's discoverable
from django.contrib.auth.models import User
# If you have a custom user model, ensure it's imported or tests might fail on User.DoesNotExist
# For example: from accounts.models import CustomUser as User (if User is not the default)
# For this project, it seems default User is fine as no custom auth is mentioned.

# More test classes will follow for other functionalities.
# For now, this sets up the file and tests the registration fee.
# Note: The force_login assumes you have 'django.contrib.auth' and its backends set up.
# If views are protected by @login_required or LoginRequiredMixin.
# If views are public, force_login is not needed.
# Based on the project structure, many views are likely admin/staff protected.
# For simplicity, I'm adding a basic user for login.
# If there's a specific 'staff' or 'admin' user type or group needed for access, that should be used.

# TODO: Add tests for:
# - Attendance registration fix (api_record_attendance view)
# - Attendance model's 'excused_absence' field
# - Student monthly payment page (GET and POST actions)
# - Teacher monthly payment page (GET and POST actions)

# To run these tests, Django's test runner will be used:
# python manage.py test school_app
# Make sure this file is in school_app/tests.py
# And that school_app is in INSTALLED_APPS
# Also, ensure migrations for the 'excused_absence' field have been created and applied to the test DB.
# If not, model tests or views using it might fail.

# The `setUp` method creates a User. If it already exists (e.g. from a previous test run if DB is not fully reset),
# this might cause an error. Test runner usually creates a fresh DB.
# If User model is custom, ensure it's the one being created.
# For now, assuming default User model.
# The force_login requires 'django.contrib.sessions' and 'django.contrib.auth' in INSTALLED_APPS
# and their migrations applied.
# If views are not login protected, then client.force_login can be removed.
# Looking at the views, they don't seem to have explicit @login_required.
# So, I will remove force_login for now, and add if tests fail due to auth.
# UPDATE: The student_payment view, for instance, doesn't have @login_required.
# So, removing force_login from the registration fee test.

class RegistrationFeeContextTests(TestCase):
    def setUp(self):
        self.student1 = Student.objects.create(
            full_name="Test StudentReg",
            phone_number="0123456789", guardian_phone="0987654321",
            birth_day=1, birth_month=1, birth_year=2000,
            academic_level=AcademicLevel.objects.create(name="Test Level", category="HIGH")
        )

    def test_registration_fee_in_context(self):
        # Test the constant value from views
        self.assertEqual(views.REGISTRATION_FEE_AMOUNT, Decimal('500.00'))

        # Test context in student_payment view
        response_payment = self.client.get(reverse('student_payment', args=[self.student1.id]))
        self.assertEqual(response_payment.status_code, 200)
        self.assertIn('REGISTRATION_FEE_AMOUNT', response_payment.context)
        self.assertEqual(response_payment.context['REGISTRATION_FEE_AMOUNT'], Decimal('500.00'))

        # Test context in print_registration_confirmation view
        self.student1.registration_fee_paid = True # Prerequisite for the print view
        self.student1.save()
        response_print = self.client.get(reverse('print_registration_confirmation', args=[self.student1.id]))
        self.assertEqual(response_print.status_code, 200)
        self.assertIn('REGISTRATION_FEE_AMOUNT', response_print.context)
        self.assertEqual(response_print.context['REGISTRATION_FEE_AMOUNT'], Decimal('500.00'))

# Note: The BasicSetupTests class was a bit too complex for just testing the fee constant.
# Separated into RegistrationFeeContextTests for clarity.
# The BasicSetupTests can be used as a base for more complex integration tests later.

# For now, I will proceed by adding tests class by class.
# Starting with Attendance Model, then Attendance API, then Student Monthly Payment, then Teacher Monthly Payment.
# I will use the BasicSetupTests as a parent class for integration tests that need a lot of pre-existing data.
# For simpler unit tests (like model field existence), a minimal setup is better.

class AttendanceModelTests(TestCase):
    def test_attendance_has_excused_absence_field(self):
        attendance = Attendance()
        self.assertTrue(hasattr(attendance, 'excused_absence'))
        self.assertFalse(attendance.excused_absence) # Check default value

    def test_attendance_creation_with_excused_absence(self):
        level = AcademicLevel.objects.create(name="Test Level", category="PRIMARY")
        student = Student.objects.create(full_name="S A", phone_number="011", guardian_phone="022", birth_day=1, birth_month=1, birth_year=2010, academic_level=level)
        subject = Subject.objects.create(name="Test Subject")
        teacher = Teacher.objects.create(full_name="T A", phone_number="033", subject=subject)
        group = Group.objects.create(name="G1", subject=subject, teacher=teacher, price_per_4_sessions=1000, session_day=1, session_start_time="10:00")
        session_obj = Session.objects.create(group=group, date=timezone.now().date(), start_time="10:00", duration=1.5)

        attendance_excused = Attendance.objects.create(
            student=student, session=session_obj, present=False, excused_absence=True
        )
        self.assertTrue(attendance_excused.excused_absence)

        attendance_not_excused = Attendance.objects.create(
            student=student, session=Session.objects.create(group=group, date=timezone.now().date() + timezone.timedelta(days=1), start_time="10:00", duration=1.5),
            present=False, excused_absence=False
        )
        self.assertFalse(attendance_not_excused.excused_absence)


class AttendanceApiTests(BasicSetupTests):
    def test_api_record_attendance_success_by_pk(self):
        # student1 is in group1, session4_g1 is a future session in group1 (no attendance yet)
        payload = {
            'session_id': self.session4_g1.id,
            'student_id': self.student1.id  # Send PK as int
        }
        response = self.client.post(
            reverse('api_record_attendance'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201) # Created
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['student_name'], self.student1.full_name)
        self.assertTrue(Attendance.objects.filter(student=self.student1, session=self.session4_g1, present=True).exists())


class SessionDeletionTests(BasicSetupTests):
    def test_session_deletion_refunds_paid_students(self):
        # Create a new student with a zero prepaid balance
        student3 = Student.objects.create(
            full_name="Refund Test Student",
            phone_number="0777123125",
            guardian_phone="0666123125",
            birth_day=1,
            birth_month=1,
            birth_year=2005,
            academic_level=self.level_high1,
            prepaid_balance=Decimal('0.00')
        )
        self.group1.students.add(student3)

        # Create a new session for the group
        session_to_delete = Session.objects.create(
            group=self.group1,
            date=timezone.now().date(),
            start_time="10:00:00",
            duration=Decimal('1.5')
        )

        # Create a paid attendance record for the student
        Attendance.objects.create(
            student=student3,
            session=session_to_delete,
            present=True,
            student_paid_for_session=True
        )

        # Ensure the student's balance is 0 before deletion
        self.assertEqual(student3.prepaid_balance, Decimal('0.00'))

        # Delete the session
        session_to_delete.delete()

        # Refresh the student object from the database
        student3.refresh_from_db()

        # Check if the student's prepaid balance has been refunded
        price_per_session = self.group1.price_per_4_sessions / Decimal('4.0')
        self.assertEqual(student3.prepaid_balance, price_per_session)


class TeacherMonthlyPaymentPageTests(BasicSetupTests):
    def setUp(self):
        super().setUp() # Call parent setUp to get all initial data
        # Make sure teacher1 attended some sessions in group1
        self.session1_g1.teacher_attended = True
        self.session1_g1.teacher_compensated = False # Ensure it's not paid yet for tests
        self.session1_g1.save()

        self.session2_g1.teacher_attended = True
        self.session2_g1.teacher_compensated = False
        self.session2_g1.save()

        self.session3_g1.teacher_attended = True # Attended, but will test payment for s1,s2
        self.session3_g1.teacher_compensated = False
        self.session3_g1.save()

        # Student2 joins group1 for more complex absence scenarios
        self.group1.students.add(self.student2)
        # student1 was absent for session2_g1 (created in BasicSetupTests). student2 will be present.
        Attendance.objects.get_or_create(student=self.student2, session=self.session2_g1, defaults={'present': True, 'student_paid_for_session': True})
        # For session3_g1, let student2 be absent
        Attendance.objects.get_or_create(student=self.student2, session=self.session3_g1, defaults={'present': False, 'student_paid_for_session': False})


    def test_get_teacher_monthly_payment_page_no_group_or_price(self):
        response = self.client.get(reverse('teacher_monthly_payment', args=[self.teacher1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"الدفع الشهري للمدرس: {self.teacher1.full_name}")
        self.assertIn('taught_groups', response.context)
        self.assertIsNone(response.context.get('selected_group'))
        self.assertIsNone(response.context.get('teacher_price_per_session_str'))

    def test_get_teacher_monthly_payment_page_with_group_and_price(self):
        price_str = "600.00"
        response = self.client.get(
            reverse('teacher_monthly_payment', args=[self.teacher1.id]),
            {'group_id': self.group1.id, 'teacher_price_per_session': price_str}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_group'], self.group1)
        self.assertEqual(response.context['teacher_price_per_session_str'], price_str)
        self.assertIn('sessions_to_display', response.context)

        sessions_display = response.context['sessions_to_display']
        # Should list session1_g1, session2_g1, session3_g1 as they are teacher_attended=True and teacher_compensated=False
        self.assertEqual(len(sessions_display), 4)

        s2_info = next((s for s in sessions_display if s['session_id'] == self.session2_g1.id), None)
        self.assertIsNotNone(s2_info)
        # Student1 was absent for session2, student2 was present
        self.assertEqual(s2_info['student_statuses'][1]['is_present'], True)
        self.assertEqual(s2_info['student_statuses'][0]['is_present'], False)

    def test_post_calculate_payment_teacher_monthly_payment(self):
        price_str = "700.00" # Teacher's price per session
        # We will pay for session1_g1 and session2_g1.
        # For session2_g1, student1 was absent. We will count this absence.

        payload = {
            'action': 'calculate_payment',
            'group_id_hidden': self.group1.id,
            'teacher_price_per_session': price_str,
            'sessions_to_pay_ids': [self.session1_g1.id, self.session2_g1.id],
        }
        response = self.client.post(reverse('teacher_monthly_payment', args=[self.teacher1.id]), data=payload)
        self.assertEqual(response.status_code, 302) # Renders page with calculation

        response = self.client.get(response.url)
        self.assertIn('calculated_payment_details', response.context)
        details = response.context['calculated_payment_details']
        self.assertEqual(details['total_payable_instances'], 3)
        self.assertEqual(details['calculated_total_payment'], str(3 * Decimal(price_str)))


    def test_post_process_payment_teacher_monthly_payment(self):
        price = Decimal("750.00")
        sessions_to_pay_ids = [self.session1_g1.id, self.session2_g1.id]

        # First, calculate the payment to populate the session
        self.client.post(reverse('teacher_monthly_payment', args=[self.teacher1.id]), data={
            'action': 'calculate_payment',
            'group_id_hidden': self.group1.id,
            'teacher_price_per_session': str(price),
            'sessions_to_pay_ids': sessions_to_pay_ids,
        })

        payload_for_processing = {
            'action': 'process_payment',
            'group_id_hidden': self.group1.id,
            'teacher_price_per_session': str(price),
        }

        response = self.client.post(reverse('teacher_monthly_payment', args=[self.teacher1.id]), data=payload_for_processing, follow=True)
        self.assertEqual(response.status_code, 200)

        self.session1_g1.refresh_from_db()
        self.session2_g1.refresh_from_db()
        self.assertTrue(self.session1_g1.teacher_compensated)
        self.assertTrue(self.session2_g1.teacher_compensated)

        self.session3_g1.refresh_from_db()
        self.assertFalse(self.session3_g1.teacher_compensated)

        messages_list = list(response.context['messages'])
        self.assertTrue(any("تم تسجيل دفع المستحقات لـ 2 حصة بنجاح" in str(msg) for msg in messages_list))

    def test_process_payment_no_sessions_selected(self):
        price_str = "700.00"
        payload = {
            'action': 'process_payment',
            'group_id_hidden': self.group1.id,
            'teacher_price_per_session': price_str,
        }
        response = self.client.post(reverse('teacher_monthly_payment', args=[self.teacher1.id]), data=payload, follow=True)
        self.assertEqual(response.status_code, 200)

        messages_list = list(response.context['messages'])
        self.assertTrue(any("تفاصيل الدفع غير متطابقة أو مفقودة" in str(msg) for msg in messages_list))

    def test_calculate_payment_no_sessions_selected(self):
        price_str = "700.00"
        payload = {
            'action': 'calculate_payment',
            'group_id_hidden': self.group1.id,
            'teacher_price_per_session': price_str,
            'sessions_to_pay_ids': [],
        }
        response = self.client.post(reverse('teacher_monthly_payment', args=[self.teacher1.id]), data=payload)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(response.url)
        messages_list = list(response.context['messages'])
        self.assertTrue(any("الرجاء اختيار حصة واحدة على الأقل للحساب" in str(msg) for msg in messages_list))


class PaymentReportPageTests(BasicSetupTests):
    def setUp(self):
        super().setUp()
        # student1: reg_fee_paid = False initially, then set to True in some tests
        # student2: reg_fee_paid = True from start

        # student1, session1_g1: present, paid
        # student1, session2_g1: absent, unpaid
        # student1, session3_g1: present, unpaid

        # Let's make student1 pay registration fee for report calculations
        self.student1.registration_fee_paid = True
        self.student1.created_at = timezone.now() # Ensure it's within current period for some tests
        self.student1.save()

        # Ensure student2's created_at is also recent for testing registration fee income
        self.student2.created_at = timezone.now() - timezone.timedelta(days=1)
        self.student2.save()

        # Teacher1 compensation for session1_g1
        self.session1_g1.teacher_compensated = True
        self.session1_g1.save()


    def test_payment_report_loads_and_basic_calculation(self):
        response = self.client.get(reverse('payment_report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "تقرير المدفوعات")

        # Expected income from registration: student1 (500) + student2 (500) = 1000
        # (Assuming REGISTRATION_FEE_AMOUNT is 500 from views)
        expected_reg_income = views.REGISTRATION_FEE_AMOUNT * 2
        self.assertEqual(response.context['income_from_registration'], expected_reg_income)

        # Expected income from sessions:
        # student1, session1_g1 is paid. Price per session = 2000/4 = 500.
        expected_session_income = self.group1.price_per_4_sessions / 4 * 1
        self.assertEqual(response.context['income_from_sessions'], expected_session_income)

        # Expected expenses (teacher payments):
        # teacher1 compensated for session1_g1. Teacher pay rate = 0.7
        # Price per session = 500. Teacher share = 500 * 0.7 = 350
        expected_teacher_expense = (self.group1.price_per_4_sessions / 4) * views.TEACHER_SESSION_PAY_RATE
        self.assertEqual(response.context['total_expenses'], expected_teacher_expense)

        total_expected_income = expected_reg_income + expected_session_income
        self.assertEqual(response.context['total_income'], total_expected_income)

        expected_net_income = total_expected_income - expected_teacher_expense
        self.assertEqual(response.context['net_income'], expected_net_income)

    def test_payment_report_custom_date_filter(self):
        # Create a session and payment outside the default "current month"
        # For this test, let's make all existing data fall outside a very narrow custom range
        # then create specific data within that range.

        # Make existing data "old"
        self.student1.created_at = timezone.now() - timezone.timedelta(days=60)
        self.student1.save()
        self.student2.created_at = timezone.now() - timezone.timedelta(days=60)
        self.student2.save()
        self.session1_g1.date = timezone.now().date() - timezone.timedelta(days=60)
        self.session1_g1.save()

        # New data for a specific period
        filter_start_date = timezone.now().date() - timezone.timedelta(days=5)
        filter_end_date = timezone.now().date() - timezone.timedelta(days=1)

        new_student = Student.objects.create(
            full_name="Filt Student", phone_number="0123", guardian_phone="0124",
            birth_day=1,birth_month=1,birth_year=2000, academic_level=self.level_high1,
            registration_fee_paid=True, created_at=timezone.now() # Within range
        )

        new_session = Session.objects.create(
            group=self.group1, date=filter_start_date + timezone.timedelta(days=1), # Within range
            start_time="10:00", duration=1.5, teacher_attended=True, teacher_compensated=True
        )
        Attendance.objects.create(student=new_student, session=new_session, present=True, student_paid_for_session=True)

        response = self.client.get(
            reverse('payment_report'),
            {
                'period': 'custom',
                'start_date': filter_start_date.strftime('%Y-%m-%d'),
                'end_date': filter_end_date.strftime('%Y-%m-%d')
            }
        )
        self.assertEqual(response.status_code, 200)

        # Expected income from registration: new_student (500)
        self.assertEqual(response.context['income_from_registration'], views.REGISTRATION_FEE_AMOUNT * 1)
        # Expected income from sessions: new_session for new_student (500)
        self.assertEqual(response.context['income_from_sessions'], self.group1.price_per_4_sessions / 4 * 1)
        # Expected expenses: new_session for teacher1 (350)
        self.assertEqual(response.context['total_expenses'], (self.group1.price_per_4_sessions / 4) * views.TEACHER_SESSION_PAY_RATE)

    def test_payment_report_excused_absence_does_not_affect_paid_income(self):
        # student1, session3_g1: present, unpaid. Mark as paid.
        att_s3 = Attendance.objects.get(student=self.student1, session=self.session3_g1)
        att_s3.student_paid_for_session = True
        att_s3.save()

        # student1, session2_g1: absent, unpaid. Mark as excused. This should NOT make it count as income.
        att_s2 = Attendance.objects.get(student=self.student1, session=self.session2_g1)
        att_s2.excused_absence = True
        att_s2.save() # Still unpaid

        response = self.client.get(reverse('payment_report'))
        self.assertEqual(response.status_code, 200)

        # Income from sessions:
        # Student1, session1_g1 (paid in setup) = 500
        # Student1, session3_g1 (paid now) = 500
        # Student1, session2_g1 (absent, unpaid, excused) = 0
        # Total = 1000
        expected_session_income = self.group1.price_per_4_sessions / 4 * 2
        self.assertEqual(response.context['income_from_sessions'], expected_session_income)


class StudentMonthlyPaymentPageTests(BasicSetupTests):
    def test_get_student_monthly_payment_page_no_group(self):
        response = self.client.get(reverse('student_monthly_payment', args=[self.student1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"الدفع الشهري للطالب: {self.student1.full_name}")
        self.assertIn('enrolled_groups', response.context)
        self.assertIsNone(response.context.get('selected_group'))

    def test_get_student_monthly_payment_page_with_group(self):
        response = self.client.get(reverse('student_monthly_payment', args=[self.student1.id]), {'group_id': self.group1.id})
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context.get('selected_group'))
        self.assertEqual(response.context['selected_group'], self.group1)
        self.assertIn('sessions_display', response.context)
        self.assertIn('net_amount_due', response.context)

        # Student1: session1 (paid), session2 (absent, unpaid), session3 (present, unpaid)
        # Price per session = 2000/4 = 500
        # Amount due should be for session2 (if not excused) + session3 = 500 + 500 = 1000
        # The view's amount_due calculation considers non-excused unpaid sessions.
        # session2_g1 is absent, not paid, not excused. session3_g1 is present, not paid, not excused.
        # Both are billable.
        expected_amount_due = self.group1.price_per_4_sessions / 4 * 2
        self.assertEqual(response.context['net_amount_due'], expected_amount_due)

        sessions_display = response.context['sessions_display'] # Displays last 8, we have 3 relevant for student1
        self.assertTrue(any(s['session_id'] == self.session3_g1.id and s['status'] == "حاضر" and not s['is_paid'] for s in sessions_display))
        self.assertTrue(any(s['session_id'] == self.session2_g1.id and s['status'] == "غائب" and not s['is_paid'] for s in sessions_display))
        self.assertTrue(any(s['session_id'] == self.session1_g1.id and s['status'] == "حاضر" and s['is_paid'] for s in sessions_display))


    def test_post_mark_excused_student_monthly_payment(self):
        # student1, session2_g1 is absent, not paid. Mark it as excused.
        attendance_s2 = Attendance.objects.get(student=self.student1, session=self.session2_g1)
        self.assertFalse(attendance_s2.excused_absence)

        response = self.client.post(
            reverse('student_monthly_payment', args=[self.student1.id]),
            data={
                'action': 'mark_excused',
                'group_id': self.group1.id, # This should be group_id_post in view, but view uses group_details
                'session_id': self.session2_g1.id
            }
        )
        self.assertEqual(response.status_code, 302) # Redirects
        expected_redirect_url = reverse('student_monthly_payment', args=[self.student1.id]) + f'?group_id={self.group1.id}'
        self.assertRedirects(response, expected_redirect_url)

        attendance_s2.refresh_from_db()
        self.assertTrue(attendance_s2.excused_absence)

        # Check amount due again, session2 should now be ignored
        response_after_excuse = self.client.get(reverse('student_monthly_payment', args=[self.student1.id]), {'group_id': self.group1.id})
        self.assertEqual(response_after_excuse.status_code, 200)
        # Only session3 (present, unpaid) should be due now
        expected_amount_due_after_excuse = self.group1.price_per_4_sessions / 4 * 1
        self.assertEqual(response_after_excuse.context['net_amount_due'], expected_amount_due_after_excuse)

    def test_post_process_payment_student_monthly_payment_exact_amount(self):
        # Student1: session2 (absent, unpaid), session3 (present, unpaid). Due = 1000. Pay 1000.
        # Price per session = 500
        amount_to_pay = self.group1.price_per_4_sessions / 4 * 2 # For session2 and session3

        response = self.client.post(
            reverse('student_monthly_payment', args=[self.student1.id]),
            data={
                'action': 'process_payment',
                'group_id': self.group1.id,
                'amount_paid': str(amount_to_pay)
            }
        )
        self.assertEqual(response.status_code, 302) # Redirects
        expected_redirect_url = reverse('student_monthly_payment', args=[self.student1.id]) + f'?group_id={self.group1.id}'
        self.assertRedirects(response, expected_redirect_url)

        att_s2 = Attendance.objects.get(student=self.student1, session=self.session2_g1)
        att_s3 = Attendance.objects.get(student=self.student1, session=self.session3_g1)
        self.assertTrue(att_s2.student_paid_for_session)
        self.assertTrue(att_s3.student_paid_for_session)

        # Check amount due again, should be 0
        response_after_payment = self.client.get(reverse('student_monthly_payment', args=[self.student1.id]), {'group_id': self.group1.id})
        self.assertEqual(response_after_payment.context['net_amount_due'], Decimal('0.00'))

    def test_post_process_payment_student_monthly_payment_overpayment(self):
        # Student1: session2 (absent, unpaid), session3 (present, unpaid). Due = 1000. Pay 1500.
        # Overpayment of 500.
        amount_to_pay = (self.group1.price_per_4_sessions / 4 * 2) + 500

        response = self.client.post(
            reverse('student_monthly_payment', args=[self.student1.id]),
            data={
                'action': 'process_payment',
                'group_id': self.group1.id,
                'amount_paid': str(amount_to_pay)
            },
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        messages_list = list(response.context['messages'])
        self.assertTrue(any("تم إضافة المبلغ المتبقي" in str(msg) and "إلى الرصيد المدفوع مقدماً" in str(msg) for msg in messages_list))

        att_s2 = Attendance.objects.get(student=self.student1, session=self.session2_g1)
        att_s3 = Attendance.objects.get(student=self.student1, session=self.session3_g1)
        self.assertTrue(att_s2.student_paid_for_session)
        self.assertTrue(att_s3.student_paid_for_session)

    def test_post_process_payment_student_monthly_payment_partial_payment(self):
        # Student1: session2 (absent, unpaid), session3 (present, unpaid). Due = 1000. Pay 500 (covers one session).
        amount_to_pay = self.group1.price_per_4_sessions / 4 * 1 # For one session

        response = self.client.post(
            reverse('student_monthly_payment', args=[self.student1.id]),
            data={
                'action': 'process_payment',
                'group_id': self.group1.id,
                'amount_paid': str(amount_to_pay)
            }
        )
        self.assertEqual(response.status_code, 302)

        att_s2 = Attendance.objects.get(student=self.student1, session=self.session2_g1) # Chronologically first unpaid
        att_s3 = Attendance.objects.get(student=self.student1, session=self.session3_g1)
        self.assertTrue(att_s2.student_paid_for_session)
        self.assertFalse(att_s3.student_paid_for_session) # Second one should still be unpaid

        response_after_payment = self.client.get(reverse('student_monthly_payment', args=[self.student1.id]), {'group_id': self.group1.id})
        expected_amount_due_after_partial = self.group1.price_per_4_sessions / 4 * 1
        self.assertEqual(response_after_payment.context['net_amount_due'], expected_amount_due_after_partial)

    def test_post_process_payment_insufficient_for_one_session(self):
        price_per_session = self.group1.price_per_4_sessions / 4
        amount_to_pay = price_per_session - 100 # Less than one session

        response = self.client.post(
            reverse('student_monthly_payment', args=[self.student1.id]),
            data={
                'action': 'process_payment',
                'group_id': self.group1.id,
                'amount_paid': str(amount_to_pay)
            },
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        messages_list = list(response.context['messages'])
        self.assertTrue(any(f"المبلغ المدفوع {amount_to_pay} غير كافٍ لدفع حصة كاملة" in str(msg) for msg in messages_list))

        att_s2 = Attendance.objects.get(student=self.student1, session=self.session2_g1)
        self.assertFalse(att_s2.student_paid_for_session) # Should not be paid


class AttendanceApiTests(BasicSetupTests): # This line was part of the original search block for the previous incorrect diff.
    def test_api_record_attendance_success_by_pk(self):
        # student1 is in group1, session4_g1 is a future session in group1 (no attendance yet)
        payload = {
            'session_id': self.session4_g1.id,
            'student_id': self.student1.id  # Send PK as int
        }
        response = self.client.post(
            reverse('api_record_attendance'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201) # Created
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['student_name'], self.student1.full_name)
        self.assertTrue(Attendance.objects.filter(student=self.student1, session=self.session4_g1, present=True).exists())

    def test_api_record_attendance_success_by_card_number(self):
        # Clean up any existing attendance for student1 and session4_g1 from other tests to ensure a clean slate
        Attendance.objects.filter(student=self.student1, session=self.session4_g1).delete()
        payload = {
            'session_id': self.session4_g1.id,
            'student_id': self.student1.card_number # Send card_number as string
        }
        response = self.client.post(
            reverse('api_record_attendance'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(Attendance.objects.filter(student=self.student1, session=self.session4_g1, present=True).exists())

    def test_api_record_attendance_already_registered(self):
        # session1_g1 already has an attendance record for student1
        payload = {
            'session_id': self.session1_g1.id,
            'student_id': self.student1.id
        }
        response = self.client.post(
            reverse('api_record_attendance'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200) # Not an error, specific status
        data = response.json()
        self.assertEqual(data['status'], 'already_registered')

    def test_api_record_attendance_student_not_found(self):
        payload = {
            'session_id': self.session1_g1.id,
            'student_id': 99999 # Non-existent student PK
        }
        response = self.client.post(
            reverse('api_record_attendance'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['message'], 'الطالب غير موجود. تحقق من الرقم المدخل أو البطاقة.')

    def test_api_record_attendance_student_not_found_by_card(self):
        payload = {
            'session_id': self.session1_g1.id,
            'student_id': "INVALIDCARD" # Non-existent card number
        }
        response = self.client.post(
            reverse('api_record_attendance'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['message'], 'الطالب غير موجود. تحقق من الرقم المدخل أو البطاقة.')

    def test_api_record_attendance_session_not_found(self):
        payload = {
            'session_id': 99999, # Non-existent session
            'student_id': self.student1.id
        }
        response = self.client.post(
            reverse('api_record_attendance'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data['message'], 'الجلسة غير موجودة.')

    def test_api_record_attendance_missing_data(self):
        payload = {'session_id': self.session1_g1.id} # Missing student_id
        response = self.client.post(reverse('api_record_attendance'), data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['message'], 'معرف الجلسة ومعرف الطالب مطلوبان.')

    def test_api_record_attendance_invalid_json(self):
        response = self.client.post(reverse('api_record_attendance'), data="not json", content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['message'], 'بيانات JSON غير صالحة.')

    def test_api_record_attendance_numeric_string_pk_lookup(self):
        # Test if student_id as a numeric string (e.g. "1") correctly finds student by PK
        Attendance.objects.filter(student=self.student1, session=self.session4_g1).delete() # cleanup
        payload = {
            'session_id': self.session4_g1.id,
            'student_id': str(self.student1.id)
        }
        response = self.client.post(
            reverse('api_record_attendance'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertTrue(Attendance.objects.filter(student=self.student1, session=self.session4_g1, present=True).exists())

    def test_api_record_attendance_numeric_string_card_number_lookup(self):
        # Create a student whose card_number is purely numeric
        numeric_card_student = Student.objects.create(
            full_name="NumericCard Student",
            phone_number="0770000001", guardian_phone="0660000001",
            birth_day=1, birth_month=1, birth_year=2003,
            academic_level=self.level_high1,
            card_number="1234567890" # Purely numeric card number
        )
        self.group1.students.add(numeric_card_student)
        Attendance.objects.filter(student=numeric_card_student, session=self.session4_g1).delete() #cleanup

        payload = {
            'session_id': self.session4_g1.id,
            'student_id': "1234567890"
        }
        response = self.client.post(
            reverse('api_record_attendance'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['student_name'], "NumericCard Student")
        self.assertTrue(Attendance.objects.filter(student=numeric_card_student, session=self.session4_g1, present=True).exists())

    def test_api_record_attendance_pk_does_not_exist_tries_card_number(self):
        non_existent_pk_matching_card = "999888777"
        self.student1.card_number = non_existent_pk_matching_card
        self.student1.save()
        Attendance.objects.filter(student=self.student1, session=self.session4_g1).delete() # cleanup

        payload = {
            'session_id': self.session4_g1.id,
            'student_id': non_existent_pk_matching_card
        }
        response = self.client.post(
            reverse('api_record_attendance'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['student_name'], self.student1.full_name)
        self.assertTrue(Attendance.objects.filter(student=self.student1, session=self.session4_g1, present=True).exists())
