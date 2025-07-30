from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import Course, Attendance, Lecturer


User = get_user_model()

class LecturerRegistrationForm(UserCreationForm):
    """Form for lecturer registration"""
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'placeholder': 'Email Address'}))
    department = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'placeholder': 'Department'}))
    phone_number = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'placeholder': 'Phone Number (Optional)'}))

    class Meta:
        model = Lecturer
        fields = ('username', 'first_name', 'last_name', 'email', 'department', 'phone_number', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-input',
                'placeholder': field.widget.attrs.get('placeholder', '')
            })
        
        # Add help text for password fields
        self.fields['password1'].help_text = 'Password must be at least 8 characters long.'
        self.fields['password2'].help_text = 'Enter the same password as before, for verification.'
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and Lecturer.objects.filter(email=email).exists():
            raise forms.ValidationError('A lecturer with this email address already exists.')
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and Lecturer.objects.filter(username=username).exists():
            raise forms.ValidationError('A lecturer with this username already exists.')
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True  # Set is_staff to True for lecturers
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone_number = self.cleaned_data['phone_number']
        user.department = self.cleaned_data['department']
        
        if commit:
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

class ResendVerificationForm(forms.Form):
    """Form for resending verification email"""
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your email address',
            'autofocus': True
        }),
        error_messages={
            'required': 'Please enter your email address.',
            'invalid': 'Please enter a valid email address.'
        }
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if not email:
            raise forms.ValidationError('Please enter your email address.')
        return email


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
