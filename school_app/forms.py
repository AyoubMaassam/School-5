# school_app/forms.py
from django import forms
from .models import Group, Subject, Teacher, AcademicLevel, Session # Added Session

class GroupForm(forms.ModelForm):
    academic_levels = forms.ModelMultipleChoiceField(
        queryset=AcademicLevel.objects.all().order_by('category', 'name'),
        widget=forms.SelectMultiple(attrs={'class': 'form-control choices-multi-select', 'size': '8'}), # Added 'choices-multi-select'
        label="المستويات الدراسية المتوافقة",
        help_text="اضغط Ctrl (أو Cmd على Mac) لاختيار أكثر من مستوى.",
        required=True # Make sure this field is required
    )

    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="المادة"
    )

    teacher = forms.ModelChoiceField(
        queryset=Teacher.objects.all().order_by('full_name'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="المدرس"
    )

    class Meta:
        model = Group
        fields = ['name', 'subject', 'teacher', 'academic_levels',
                  'price_per_4_sessions', 'session_day',
                  'session_start_time', 'session_duration',
                  'is_continuous', 'created_sessions_until']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'price_per_4_sessions': forms.NumberInput(attrs={'class': 'form-control'}),
            'session_day': forms.Select(attrs={'class': 'form-control'}),
            'session_start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'session_duration': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_continuous': forms.CheckboxInput(attrs={'class': 'custom-control-input'}),
            'created_sessions_until': forms.DateInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'type': 'date'}),
        }
        labels = {
            'name': "اسم الفوج",
            'price_per_4_sessions': "السعر لكل 4 حصص (بالدينار)",
            'session_day': "يوم الحصة الأسبوعية",
            'session_start_time': "وقت بداية الحصة",
            'session_duration': "مدة الحصة (بالساعات)",
            'is_continuous': "فوج مستمر (تُنشأ الحصص أسبوعياً تلقائياً)",
            'created_sessions_until': "تم إنشاء الحصص حتى تاريخ (للعرض فقط)",
        }
        help_texts = {
            'session_start_time': 'استخدم تنسيق HH:MM (مثال: 14:30)',
            'is_continuous': 'إذا تم تحديده، سيقوم النظام بمحاولة إنشاء حصص لهذا الفوج أسبوعياً بشكل تلقائي.',
        }

    def __init__(self, *args, **kwargs):
        super(GroupForm, self).__init__(*args, **kwargs)
        # Ensure subject and teacher querysets are ordered for consistency if not explicitly defined above
        if 'subject' in self.fields:
            self.fields['subject'].queryset = Subject.objects.all().order_by('name')
        if 'teacher' in self.fields:
            self.fields['teacher'].queryset = Teacher.objects.all().order_by('full_name')

        # If you want to dynamically filter teachers based on subject (requires more complex JS or a page reload approach)
        # This form is for server-rendered editing, so dynamic filtering isn't straightforward without JS.
        # For now, it lists all teachers.

        # Ensure academic_levels is marked as required if it is.
        # The field definition above already sets required=True by default for ModelMultipleChoiceField
        # unless allow_empty=True is specified.
        if 'academic_levels' in self.fields:
             self.fields['academic_levels'].required = True
             if not self.fields['academic_levels'].help_text:
                self.fields['academic_levels'].help_text = "اختر مستوى دراسي واحد على الأقل."

        if 'created_sessions_until' in self.fields:
            self.fields['created_sessions_until'].required = False


    def clean_academic_levels(self):
        academic_levels = self.cleaned_data.get('academic_levels')
        if not academic_levels: # This validation is now also handled by required=True on the field
            raise forms.ValidationError("يجب اختيار مستوى دراسي واحد على الأقل.")
        return academic_levels

class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['group', 'date', 'start_time', 'duration', 'teacher_attended']
        widgets = {
            'group': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'duration': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25'}),
            'teacher_attended': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'group': "الفوج",
            'date': "التاريخ",
            'start_time': "وقت البدء",
            'duration': "المدة (ساعات)",
            'teacher_attended': "حضور المدرس؟",
        }
        help_texts = {
            'start_time': 'استخدم تنسيق HH:MM (مثال: 14:30)',
        }

    def __init__(self, *args, **kwargs):
        super(SessionForm, self).__init__(*args, **kwargs)
        self.fields['group'].queryset = Group.objects.all().order_by('name')
        # For teacher_attended, CheckboxInput handles False if unchecked.
        # If the model field `teacher_attended` is a NullBooleanField,
        # and you want to explicitly submit None, use NullBooleanSelect.
        # Otherwise, this setup is fine; if not checked, it will save as False.
        # If it's a BooleanField(null=True, blank=True) and required=False on form field,
        # it can be tricky with CheckboxInput. Default model form field for BooleanField is CheckboxInput.
        # For nullable Booleans, often a Select widget with (Yes, No, Unknown) is clearer
        # or ensure the model field default handles the "unknown" state if checkbox is not used.
        # Given `teacher_attended = models.BooleanField(null=True, blank=True)`,
        # making the form field not required allows it to be un Ticked (False) or not present.
        # However, CheckboxInput sends 'on' or nothing. Django interprets 'nothing' as False for BooleanFields
        # if it's not a NullBooleanField with NullBooleanSelect.
        # To allow explicitly setting it to None (Unknown) vs False (No), you might need custom handling or widget.
        # For now, we assume False if unchecked is fine.
        self.fields['teacher_attended'].required = False
