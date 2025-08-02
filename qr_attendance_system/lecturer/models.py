from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class Lecturer(AbstractUser):
    """Custom User model for lecturers"""
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    department = models.CharField(max_length=100)
    email_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, blank=True, null=True)
    verification_token_created = models.DateTimeField(blank=True, null=True)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    verification_code_created = models.DateTimeField(blank=True, null=True)
    
    # Fields for email change verification
    new_email = models.EmailField(blank=True, null=True)
    email_change_token = models.CharField(max_length=100, blank=True, null=True)
    email_change_token_created = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Lecturer'
        verbose_name_plural = 'Lecturers'
        
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"
        
    def initiate_email_change(self, new_email, request=None):
        """
        Initiate an email change request.
        Returns (success: bool, error_message: str)
        """
        from django.utils import timezone
        from .utils import generate_verification_token
        
        try:
            # Check if the new email is already in use
            if Lecturer.objects.filter(email=new_email).exclude(pk=self.pk).exists():
                return False, 'This email is already in use by another account.'
                
            # Set new email and generate verification token
            self.new_email = new_email
            self.email_change_token = generate_verification_token()
            self.email_change_token_created = timezone.now()
            self.save()
            
            # Send verification email to the new email address
            if request:
                from .utils import send_email_change_verification
                success, error_msg = send_email_change_verification(request, self)
                if not success:
                    return False, f'Failed to send verification email: {error_msg}'
                    
            return True, 'Verification email has been sent to your new email address.'
            
        except Exception as e:
            return False, f'An error occurred: {str(e)}'
    
    def confirm_email_change(self, token):
        """
        Confirm and complete the email change using the verification token.
        Returns (success: bool, error_message: str)
        """
        from django.utils import timezone
        from datetime import timedelta
        
        try:
            # Check if there's a pending email change
            if not self.new_email or not self.email_change_token:
                return False, 'No pending email change request found.'
            
            # Verify the token
            if self.email_change_token != token:
                return False, 'Invalid verification token.'
                
            # Check if token is expired (15 minutes)
            if (timezone.now() - self.email_change_token_created) > timedelta(minutes=15):
                self.email_change_token = None
                self.email_change_token_created = None
                self.save()
                return False, 'The verification link has expired. Please request a new email change.'
            
            # Update email and clear change fields
            old_email = self.email
            self.email = self.new_email
            self.email_verified = True
            self.new_email = None
            self.email_change_token = None
            self.email_change_token_created = None
            self.save()
            
            # Send notification to old email (optional)
            # send_email_change_notification(self, old_email)
            
            return True, 'Your email address has been updated successfully.'
            
        except Exception as e:
            return False, f'An error occurred: {str(e)}'

    # Override inherited fields to set related_names
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name='lecturer_set',
        related_query_name='lecturer'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='lecturer_set',
        related_query_name='lecturer'
    )


class Course(models.Model):
    """Model to store course information"""
    lecturer = models.ForeignKey(Lecturer, on_delete=models.CASCADE, related_name='courses')
    title = models.CharField(max_length=200)
    day = models.CharField(max_length=20, choices=[
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday')
    ])
    start_time = models.TimeField()
    end_time = models.TimeField()
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    qr_code_url = models.URLField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.title} - {self.day} {self.start_time}"


class Attendance(models.Model):
    """Model to store student attendance records"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='attendances')
    student_name = models.CharField(max_length=100)
    student_admin_no = models.CharField(max_length=20)
    timestamp = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.student_name} - {self.course.title} ({self.timestamp.date()})"


class LoginLog(models.Model):
    """Model to store lecturer login/logout audit trail"""
    lecturer = models.ForeignKey(Lecturer, on_delete=models.CASCADE, related_name='login_logs')
    action = models.CharField(max_length=10, choices=[
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('failed', 'Failed Login')
    ])
    timestamp = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Login Log'
        verbose_name_plural = 'Login Logs'
    
    def __str__(self):
        return f"{self.lecturer.username} - {self.action} - {self.timestamp}"


class LoginAttempt(models.Model):
    """Model to track login attempts for rate limiting"""
    ip_address = models.GenericIPAddressField()
    username = models.CharField(max_length=150, blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    successful = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Login Attempt'
        verbose_name_plural = 'Login Attempts'
    
    def __str__(self):
        status = "Success" if self.successful else "Failed"
        return f"{self.ip_address} - {self.username or 'Unknown'} - {status} - {self.timestamp}"
