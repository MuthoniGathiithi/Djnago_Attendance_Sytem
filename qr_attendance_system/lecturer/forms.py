from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Course, Attendance


User = get_user_model()

class LecturerRegistrationForm(UserCreationForm):
    """Form for lecturer registration"""
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'placeholder': 'Email Address'}))
    department = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'placeholder': 'Department'}))
    phone_number = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'placeholder': 'Phone Number (Optional)'}))

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'department', 'phone_number', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-input',
                'placeholder': field.widget.attrs.get('placeholder', '')
            })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True  # Set is_staff to True for lecturers
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Save additional lecturer fields
            user.phone_number = self.cleaned_data['phone_number']
            user.department = self.cleaned_data['department']
            user.save()
        
        return user

class CourseForm(forms.ModelForm):
    """Form for creating and updating courses"""
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Course Title (e.g., "Networking Fundamentals")'
        })
    )
    day = forms.ChoiceField(
        choices=[
            ('Monday', 'Monday'),
            ('Tuesday', 'Tuesday'),
            ('Wednesday', 'Wednesday'),
            ('Thursday', 'Thursday'),
            ('Friday', 'Friday'),
            ('Saturday', 'Saturday'),
            ('Sunday', 'Sunday')
        ],
        widget=forms.Select(attrs={'class': 'form-input'})
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'class': 'form-input',
            'type': 'time'
        })
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'class': 'form-input',
            'type': 'time'
        })
    )

    class Meta:
        model = Course
        fields = ('title', 'day', 'start_time', 'end_time')

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and end_time <= start_time:
            raise forms.ValidationError('End time must be after start time.')

        return cleaned_data

class QRCodeGenerationForm(forms.Form):
    """Form for generating QR codes"""
    class Meta:
        fields = ()  # No fields needed as we'll generate QR code directly from course data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['qr_code'].widget.attrs.update({'class': 'form-input'})

class AttendanceForm(forms.ModelForm):
    """Form for student attendance submission"""
    student_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your full name'
        })
    )
    student_admin_no = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your student ID'
        })
    )

    class Meta:
        model = Attendance
        fields = ('student_name', 'student_admin_no')

    def __init__(self, *args, **kwargs):
        self.course = kwargs.pop('course', None)
        super().__init__(*args, **kwargs)
        self.fields['student_name'].widget.attrs.update({'autofocus': True})

    def clean_student_admin_no(self):
        admin_no = self.cleaned_data.get('student_admin_no')
        if not admin_no:
            raise forms.ValidationError('Student ID is required')
        return admin_no

    def save(self, commit=True):
        attendance = super().save(commit=False)
        if self.course:
            attendance.course = self.course
        if commit:
            attendance.save()
        return attendance
