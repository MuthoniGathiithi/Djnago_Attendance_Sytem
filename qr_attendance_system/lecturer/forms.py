from django import forms
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm, PasswordChangeForm
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from .models import Course, Attendance, Lecturer


User = get_user_model()

class LecturerRegistrationForm(UserCreationForm):
    """Form for lecturer registration"""
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'placeholder': 'Email Address'}))
    department = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'placeholder': 'Department'}))

    class Meta:
        model = Lecturer
        fields = ('first_name', 'last_name', 'email', 'department', 'password1', 'password2')

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
        # Temporarily disabled for debugging
        # if email and Lecturer.objects.filter(email=email).exists():
        #     raise forms.ValidationError('A lecturer with this email address already exists.')
        print(f"DEBUG: Checking email {email}")
        from lecturer.models import Lecturer
        existing_count = Lecturer.objects.filter(email=email).count()
        print(f"DEBUG: Found {existing_count} lecturers with email {email}")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Auto-generate username from email address
        email = self.cleaned_data['email']
        base_username = email.split('@')[0]  # Use part before @ as base username
        username = base_username
        
        # Ensure username is unique by adding a number if needed
        counter = 1
        while Lecturer.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        user.username = username
        user.is_staff = True  # Set is_staff to True for lecturers
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
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
        try:
            user = Lecturer.objects.get(email=email)
            if user.email_verified:
                raise forms.ValidationError('This email is already verified.')
        except Lecturer.DoesNotExist:
            # Don't reveal if email exists or not for security
            pass
        return email


class EmailChangeForm(forms.Form):
    """Form for changing user's email address"""
    current_password = forms.CharField(
        label=_("Current password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'current-password',
            'class': 'form-input',
            'placeholder': 'Enter your current password'
        }),
    )
    
    new_email = forms.EmailField(
        label=_("New email address"),
        max_length=254,
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
            'class': 'form-input',
            'placeholder': 'Enter your new email address'
        }),
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_current_password(self):
        """
        Validate that the current_password field is correct.
        """
        current_password = self.cleaned_data.get("current_password")
        if not self.user.check_password(current_password):
            raise forms.ValidationError(
                _("Your current password was entered incorrectly. Please enter it again."),
                code='password_incorrect',
            )
        return current_password
    
    def clean_new_email(self):
        """
        Validate that the new email is not already in use.
        """
        new_email = self.cleaned_data.get('new_email')
        
        # Check if the new email is the same as the current one
        if new_email.lower() == self.user.email.lower():
            raise forms.ValidationError(
                _("This is already your current email address.")
            )
        
        # Check if the new email is already in use by another account
        if Lecturer.objects.filter(email__iexact=new_email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError(
                _("This email is already in use by another account.")
            )
            
        return new_email.lower()
    
    def save(self, commit=True):
        """
        Initiate the email change process.
        Returns (success: bool, message: str)
        """
        try:
            new_email = self.cleaned_data['new_email']
            return self.user.initiate_email_change(new_email, self.request)
        except Exception as e:
            if settings.DEBUG:
                return False, str(e)
            return False, _("An error occurred while processing your request. Please try again later.")


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
