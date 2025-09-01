from django.db import models, transaction
from django.utils import timezone
from decimal import Decimal

class AcademicLevel(models.Model):
    name = models.CharField(max_length=100, verbose_name="الاسم")
    category = models.CharField(max_length=50, choices=[
        ('PRIMARY', 'ابتدائي'),
        ('MIDDLE', 'متوسط'),
        ('HIGH', 'ثانوي')
    ], verbose_name="الفئة")
    
    def __str__(self):
        return f"{self.get_category_display()} - {self.name}"

    class Meta:
        verbose_name = "المستوى الدراسي"
        verbose_name_plural = "المستويات الدراسية"

class Subject(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم المادة")
    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "مادة دراسية"
        verbose_name_plural = "المواد الدراسية"

class Student(models.Model):
    full_name = models.CharField(max_length=201, verbose_name="الاسم الكامل")
    phone_number = models.CharField(max_length=20, null=True, blank=True, verbose_name="رقم هاتف الطالب")
    guardian_phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="رقم هاتف الولي")
    birth_day = models.IntegerField(verbose_name="يوم الميلاد")
    birth_month = models.IntegerField(verbose_name="شهر الميلاد")
    birth_year = models.IntegerField(verbose_name="سنة الميلاد")
    academic_level = models.ForeignKey(AcademicLevel, on_delete=models.PROTECT, verbose_name="المستوى الدراسي")
    registration_fee_paid = models.BooleanField(default=False, verbose_name="رسوم التسجيل مدفوعة")
    card_number = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="رقم البطاقة")
    prepaid_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="رصيد مدفوع مقدماً")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    
    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "طالب"
        verbose_name_plural = "الطلاب"

class Teacher(models.Model):
    full_name = models.CharField(max_length=201, verbose_name="الاسم الكامل")
    phone_number = models.CharField(max_length=20, unique=True, verbose_name="رقم الهاتف")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, verbose_name="المادة الأساسية")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    
    def __str__(self):
        return f"{self.full_name} - {self.subject}"

    class Meta:
        verbose_name = "مدرس"
        verbose_name_plural = "المدرسون"

class Group(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم الفوج")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, verbose_name="المادة")
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, verbose_name="المدرس")
    academic_levels = models.ManyToManyField(AcademicLevel, verbose_name="المستويات الدراسية المتوافقة")
    price_per_4_sessions = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="السعر لكل 4 حصص")
    session_day = models.IntegerField(choices=[
        (0, 'الاثنين'),
        (1, 'الثلاثاء'),
        (2, 'الأربعاء'),
        (3, 'الخميس'),
        (4, 'الجمعة'),
        (5, 'السبت'),
        (6, 'الأحد')
    ], verbose_name="يوم الحصة")
    session_start_time = models.TimeField(verbose_name="وقت بداية الحصة")
    session_duration = models.DecimalField(max_digits=4, decimal_places=2, default=1.5, verbose_name="مدة الحصة (ساعات)")
    students = models.ManyToManyField(Student, through='StudentGroup', blank=True, verbose_name="الطلاب المسجلون")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    is_continuous = models.BooleanField(default=False, verbose_name="فوج مستمر (تُنشأ الحصص أسبوعياً تلقائياً)")
    created_sessions_until = models.DateField(null=True, blank=True, verbose_name="تم إنشاء الحصص حتى تاريخ")
    
    def __str__(self):
        return f"{self.name} - {self.subject}"

    class Meta:
        verbose_name = "فوج"
        verbose_name_plural = "الأفواج"


class StudentGroup(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="الطالب")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, verbose_name="الفوج")
    enrollment_date = models.DateField(auto_now_add=True, verbose_name="تاريخ التسجيل في الفوج")

    class Meta:
        unique_together = ('student', 'group')
        verbose_name = "تسجيل طالب في فوج"
        verbose_name_plural = "تسجيلات الطلاب في الأفواج"

    def __str__(self):
        return f"{self.student} enrolled in {self.group} on {self.enrollment_date}"

class Session(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='sessions', verbose_name="الفوج")
    date = models.DateField(verbose_name="التاريخ")
    start_time = models.TimeField(verbose_name="وقت البدء")
    duration = models.DecimalField(max_digits=4, decimal_places=2, verbose_name="المدة (ساعات)")
    teacher_attended = models.BooleanField(default=True, verbose_name="حضور المدرس")
    teacher_compensated = models.BooleanField(default=False, verbose_name="تم تعويض المدرس")
    teacher_payment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="المبلغ المدفوع للمدرس")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    
    def __str__(self):
        return f"{self.group.name} - {self.date} {self.start_time}"

    class Meta:
        verbose_name = "حصة"
        verbose_name_plural = "الحصص"

    def present_students_count(self):
        return self.attendance_set.filter(present=True).count()

    def absent_students_count(self):
        return self.attendance_set.filter(present=False).count()

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            # Check if the group and price are valid before proceeding
            if self.group and self.group.price_per_4_sessions and self.group.price_per_4_sessions > 0:
                price_per_session = self.group.price_per_4_sessions / Decimal('4.0')

                # Find all paid attendance records for this session
                paid_attendances = self.attendance_set.filter(student_paid_for_session=True)

                for attendance in paid_attendances:
                    student = attendance.student
                    student.prepaid_balance += price_per_session
                    student.save(update_fields=['prepaid_balance'])

            # After handling refunds, proceed with the actual deletion
            super(Session, self).delete(*args, **kwargs)

class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="الطالب")
    session = models.ForeignKey(Session, on_delete=models.CASCADE, verbose_name="الحصة")
    present = models.BooleanField(default=True, verbose_name="حاضر")
    student_paid_for_session = models.BooleanField(default=False, verbose_name="الطالب دفع للحصة")
    student_absent_and_forced_paid = models.BooleanField(default=False, verbose_name="الطالب غائب والدفع إجباري")
    excused_absence = models.BooleanField(default=False, verbose_name="غياب مبرر") # New field for excused/not counted absences
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التسجيل")
    
    class Meta:
        unique_together = ('student', 'session')
        verbose_name = "سجل حضور"
        verbose_name_plural = "سجلات الحضور"
    
    def __str__(self):
        status = "حاضر" if self.present else "غائب"
        return f"{self.student} - {self.session} - {status}"

class ActionLog(models.Model):
    ACTION_TYPE_CHOICES = [
        ('student_added', 'إنشاء حساب طالب'),
        ('student_updated', 'تحديث بيانات طالب'),
        ('student_enrolled', 'تسجيل طالب في فوج'),
        ('student_deleted', 'حذف طالب'),
        ('teacher_added', 'إضافة مدرس'),
        ('teacher_updated', 'تحديث بيانات مدرس'),
        ('teacher_deleted', 'حذف مدرس'),
        ('group_added', 'إنشاء فوج جديد'),
        ('group_updated', 'تحديث بيانات فوج'),
        ('group_deleted', 'حذف فوج'),
        ('session_added', 'إنشاء حصة'),
        ('session_updated', 'تحديث بيانات حصة'),
        ('session_deleted', 'حذف حصة'),
        ('attendance_recorded', 'تسجيل حضور وغياب'),
        ('payment_recorded', 'تسجيل دفعة مالية'),
        ('registration_fee_paid', 'دفع رسوم التسجيل'),
        ('group_session_payment_processed', 'تسجيل دفعات حصص فوج'),
        ('teacher_payment_processed', 'دفع مستحقات مدرس'),
        ('user_login', 'تسجيل دخول مستخدم'),
        ('user_logout', 'تسجيل خروج مستخدم'),
        ('report_generated', 'إنشاء تقرير'),
        ('unknown_action', 'إجراء غير معروف'),
    ]


    action_time = models.DateTimeField(auto_now_add=True, help_text="وقت حدوث الإجراء.", verbose_name="وقت الإجراء")
    action_type = models.CharField(
        max_length=100,
        choices=ACTION_TYPE_CHOICES,
        default='unknown_action', # Optional: a default
        help_text="نوع الإجراء الذي تم تنفيذه.",
        verbose_name="نوع الإجراء"
    )
    object_name = models.CharField(max_length=255, blank=True, help_text="اسم أو معرف الكائن المتأثر (طالب، فوج، إلخ).", verbose_name="اسم الكائن")
    details = models.TextField(blank=True, help_text="تفاصيل إضافية حول الحدث.", verbose_name="التفاصيل")

    def __str__(self):
        return f"{self.action_time.strftime('%Y-%m-%d %H:%M:%S')} - {self.get_action_type_display()} - {self.object_name}"

    class Meta:
        ordering = ['-action_time']
        verbose_name = "سجل إجراء"
        verbose_name_plural = "سجلات الإجراءات"