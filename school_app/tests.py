from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
import json
import datetime
from datetime import timedelta

from .models import Student, Teacher, AcademicLevel, Subject, Group, Session, Attendance, StudentGroup
from . import views

class AttendanceFixesTests(TestCase):
    def setUp(self):
        self.level = AcademicLevel.objects.create(name="Test Level", category="HIGH")
        self.subject = Subject.objects.create(name="Test Subject")
        self.teacher = Teacher.objects.create(full_name="Test Teacher", phone_number="0123456789", subject=self.subject)
        self.group = Group.objects.create(
            name="Test Group", subject=self.subject, teacher=self.teacher,
            price_per_4_sessions=Decimal('2000.00'), session_day=0, session_start_time="10:00:00"
        )
        self.student = Student.objects.create(
            full_name="Test Student", phone_number="0987654321", guardian_phone="0987654322",
            birth_day=1, birth_month=1, birth_year=2000, academic_level=self.level,
            card_number="CARD-001"
        )
        self.enrollment_date = timezone.now().date() - timedelta(days=30)
        StudentGroup.objects.create(student=self.student, group=self.group, enrollment_date=self.enrollment_date)

        self.current_session = Session.objects.create(
            group=self.group, date=timezone.now().date(),
            start_time=(timezone.now() - timedelta(minutes=5)).time(),
            duration=1.5
        )

    def test_attendance_deducts_from_prepaid_balance(self):
        price_per_session = self.group.price_per_4_sessions / Decimal('4.0')
        self.student.prepaid_balance = price_per_session * 2
        self.student.save()
        initial_balance = self.student.prepaid_balance
        payload = {'student_identifier': self.student.card_number}
        response = self.client.post(reverse('api_record_attendance_by_student'), data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['payment_status_message'], "تم الدفع من الرصيد المسبق")
        self.student.refresh_from_db()
        self.assertEqual(self.student.prepaid_balance, initial_balance - price_per_session)
        attendance = Attendance.objects.get(student=self.student, session=self.current_session)
        self.assertTrue(attendance.student_paid_for_session)

    def test_attendance_unpaid_if_balance_insufficient(self):
        price_per_session = self.group.price_per_4_sessions / Decimal('4.0')
        self.student.prepaid_balance = price_per_session - Decimal('1.00')
        self.student.save()
        initial_balance = self.student.prepaid_balance
        payload = {'student_identifier': self.student.card_number}
        response = self.client.post(reverse('api_record_attendance_by_student'), data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['payment_status_message'], "الحصة غير مدفوعة")
        self.student.refresh_from_db()
        self.assertEqual(self.student.prepaid_balance, initial_balance)
        attendance = Attendance.objects.get(student=self.student, session=self.current_session)
        self.assertFalse(attendance.student_paid_for_session)

    def test_already_registered_notification_for_unpaid_session(self):
        Attendance.objects.create(student=self.student, session=self.current_session, present=True, student_paid_for_session=False)
        payload = {'student_identifier': self.student.card_number}
        response = self.client.post(reverse('api_record_attendance_by_student'), data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'already_registered')
        self.assertEqual(data['payment_status_message'], "الحصة غير مدفوعة")

    def test_already_registered_notification_for_paid_session(self):
        Attendance.objects.create(student=self.student, session=self.current_session, present=True, student_paid_for_session=True)
        payload = {'student_identifier': self.student.card_number}
        response = self.client.post(reverse('api_record_attendance_by_student'), data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'already_registered')
        self.assertEqual(data['payment_status_message'], "")

class IsolatedFailureTest(TestCase):
    def test_get_student_monthly_payment_page_with_group(self):
        level = AcademicLevel.objects.create(name="ISO Level", category="HIGH")
        subject = Subject.objects.create(name="ISO Subject")
        teacher = Teacher.objects.create(full_name="ISO Teacher", phone_number="1111111111", subject=subject)
        group = Group.objects.create(
            name="ISO Group", subject=subject, teacher=teacher,
            price_per_4_sessions=Decimal('4000.00'),
            session_day=1, session_start_time="12:00:00"
        )
        student = Student.objects.create(
            full_name="ISO Student", phone_number="2222222222", guardian_phone="3333333333",
            birth_day=1, birth_month=1, birth_year=2001, academic_level=level
        )

        enrollment_date = datetime.date(2025, 1, 1)
        StudentGroup.objects.create(student=student, group=group, enrollment_date=enrollment_date)

        session1 = Session.objects.create(group=group, date=datetime.date(2025, 8, 10), start_time="12:00", duration=1.5)
        session2 = Session.objects.create(group=group, date=datetime.date(2025, 8, 17), start_time="12:00", duration=1.5)

        Attendance.objects.create(student=student, session=session1, present=True, student_paid_for_session=False)
        Attendance.objects.create(student=student, session=session2, present=False, student_paid_for_session=False)

        response = self.client.get(reverse('student_monthly_payment', args=[student.id]), {'group_id': group.id})

        self.assertEqual(response.status_code, 200)
        self.assertIn('net_amount_due', response.context)
        expected_amount_due = group.price_per_4_sessions / 4 * 2
        self.assertEqual(response.context['net_amount_due'], expected_amount_due)

    def test_payment_report_loads(self):
        response = self.client.get(reverse('payment_report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "التقارير المالية")
