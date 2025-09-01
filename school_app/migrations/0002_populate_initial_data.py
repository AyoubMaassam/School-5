from django.db import migrations

def populate_academic_levels_and_subjects(apps, schema_editor):
    AcademicLevel = apps.get_model('school_app', 'AcademicLevel')
    Subject = apps.get_model('school_app', 'Subject')

    # Academic Levels
    levels_data = [
        # الابتدائي
        {'name': 'السنة الأولى', 'category': 'PRIMARY'},
        {'name': 'السنة الثانية', 'category': 'PRIMARY'},
        {'name': 'السنة الثالثة', 'category': 'PRIMARY'},
        {'name': 'السنة الرابعة', 'category': 'PRIMARY'},
        {'name': 'السنة الخامسة', 'category': 'PRIMARY'},
        # المتوسط
        # For AcademicLevel, the combination of 'name' and 'category' should be unique if they are not already.
        # If 'name' alone is unique, this will cause issues. The original instruction implies 'name' and 'category' are what define a level.
        # The update_or_create call below uses both name and category in the lookup, which is correct.
        {'name': 'السنة الأولى', 'category': 'MIDDLE'},
        {'name': 'السنة الثانية', 'category': 'MIDDLE'},
        {'name': 'السنة الثالثة', 'category': 'MIDDLE'},
        {'name': 'السنة الرابعة', 'category': 'MIDDLE'},
        # الثانوي
        {'name': 'السنة الأولى المشتركة', 'category': 'HIGH'},
        {'name': 'السنة الثانية (علوم تجريبية)', 'category': 'HIGH'},
        {'name': 'السنة الثانية (رياضيات)', 'category': 'HIGH'},
        {'name': 'السنة الثانية (آداب وفلسفة)', 'category': 'HIGH'},
        {'name': 'السنة الثانية (تسيير واقتصاد)', 'category': 'HIGH'},
        {'name': 'السنة الثانية (لغات أجنبية)', 'category': 'HIGH'},
        {'name': 'السنة الثانية (تقني رياضي)', 'category': 'HIGH'},
        {'name': 'السنة الثالثة (علوم تجريبية)', 'category': 'HIGH'},
        {'name': 'السنة الثالثة (رياضيات)', 'category': 'HIGH'},
        {'name': 'السنة الثالثة (آداب وفلسفة)', 'category': 'HIGH'},
        {'name': 'السنة الثالثة (تسيير واقتصاد)', 'category': 'HIGH'},
        {'name': 'السنة الثالثة (لغات أجنبية)', 'category': 'HIGH'},
        {'name': 'السنة الثالثة (تقني رياضي)', 'category': 'HIGH'},
    ]
    for level_info in levels_data:
        # Using both name and category for the lookup to ensure distinct entries for e.g. "السنة الأولى (PRIMARY)" vs "السنة الأولى (MIDDLE)"
        AcademicLevel.objects.update_or_create(name=level_info['name'], category=level_info['category'], defaults=level_info)

    # Subjects
    subjects_data = [
        'رياضيات', 'فيزياء', 'لغة عربية', 'لغة فرنسية', 'لغة إنجليزية',
        'علوم طبيعية', 'تاريخ وجغرافيا', 'تربية إسلامية', 'تربية مدنية',
        'رسم', 'موسيقى',
        'فلسفة', 'اقتصاد ومناجمنت', 'قانون', 'هندسة ميكانيكية', 'هندسة كهربائية', 'هندسة مدنية', 'هندسة الطرائق'
    ]
    for subject_name in subjects_data:
        Subject.objects.update_or_create(name=subject_name)

class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(populate_academic_levels_and_subjects),
    ]
