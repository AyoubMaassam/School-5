from django.db import migrations, models

def combine_student_names(apps, schema_editor):
    Student = apps.get_model('school_app', 'Student')
    for student in Student.objects.all():
        student.full_name = f"{student.first_name} {student.last_name}"
        student.save()

def combine_teacher_names(apps, schema_editor):
    Teacher = apps.get_model('school_app', 'Teacher')
    for teacher in Teacher.objects.all():
        teacher.full_name = f"{teacher.first_name} {teacher.last_name}"
        teacher.save()

def do_nothing(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0016_alter_session_teacher_attended'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='full_name',
            field=models.CharField(max_length=201, null=True),
        ),
        migrations.AddField(
            model_name='teacher',
            name='full_name',
            field=models.CharField(max_length=201, null=True),
        ),
        migrations.RunPython(combine_student_names, reverse_code=do_nothing),
        migrations.RunPython(combine_teacher_names, reverse_code=do_nothing),
        migrations.RemoveField(
            model_name='student',
            name='first_name',
        ),
        migrations.RemoveField(
            model_name='student',
            name='last_name',
        ),
        migrations.RemoveField(
            model_name='teacher',
            name='first_name',
        ),
        migrations.RemoveField(
            model_name='teacher',
            name='last_name',
        ),
        migrations.AlterField(
            model_name='student',
            name='full_name',
            field=models.CharField(max_length=201, verbose_name='الاسم الكامل'),
        ),
        migrations.AlterField(
            model_name='teacher',
            name='full_name',
            field=models.CharField(max_length=201, verbose_name='الاسم الكامل'),
        ),
    ]
