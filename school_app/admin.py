from django.contrib import admin
from .models import Student, Teacher, AcademicLevel, Subject, Group, Session, Attendance

admin.site.register(Student)
admin.site.register(Teacher)
admin.site.register(AcademicLevel)
admin.site.register(Subject)
admin.site.register(Group)
admin.site.register(Session)
admin.site.register(Attendance)