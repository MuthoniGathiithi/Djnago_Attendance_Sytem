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
    
    # Fields for login attempt tracking
    failed_login_attempts = models.PositiveIntegerField(default=0)
    last_failed_login = models.DateTimeField(blank=True, null=True)
    account_locked_until = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Lecturer'
        verbose_name_plural = 'Lecturers'
        
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"
        
    def initiate_email_change(self, new_email, request=None):
        """
        Initiate the email change process by generating a token and setting the new email.
        Also generates a 6-digit verification code as a fallback.
        Returns (success, message) tuple.
        """
        # Check if the new email is already in use by another account
        if Lecturer.objects.filter(email=new_email).exclude(pk=self.pk).exists():
            return False, 'This email is already in use by another account.'
            
        self.new_email = new_email
        self.email_change_token = self._generate_verification_token()
        self.email_change_token_created = timezone.now()
        
        # Generate a 6-digit verification code
        import random
        self.email_verification_code = str(random.randint(100000, 999999))
        self.email_verification_code_created = timezone.now()
        
        self.save()
        
        if request:
            from .utils import send_email_change_verification
            success, error_msg = send_email_change_verification(request, self)
            if not success:
                return False, f'Failed to send verification email: {error_msg}'
        
        return True, 'Email change initiated successfully.'
    
    def confirm_email_change(self, verification_code=None):
        """
        Confirm and complete the email change process.
        Can be verified using either the token (from email link) or verification code.
        Returns (success, message) tuple.
        """
        if not self.new_email or (not self.email_change_token and not verification_code):
            return False, 'No pending email change to confirm.'
            
        # If using verification code
        if verification_code:
            if not self.email_verification_code or self.email_verification_code != verification_code:
                return False, 'Invalid verification code.'
                
            # Check if code is expired (15 minutes)
            code_age = timezone.now() - self.email_verification_code_created
            if code_age > timezone.timedelta(minutes=15):
                self._clear_email_change_data()
                return False, 'The verification code has expired. Please request a new one.'
        else:
            # Using token (from email link)
            if not self.email_change_token:
                return False, 'Invalid verification link.'
                
            # Verify the token is still valid (15 minutes expiration)
            token_age = timezone.now() - self.email_change_token_created
            if token_age > timezone.timedelta(minutes=15):
                self._clear_email_change_data()
                return False, 'The email change link has expired. Please request a new one.'
        
        # Update the email
        old_email = self.email
        self.email = self.new_email
        
        # Clear all verification data
        self._clear_email_change_data()
        
        return True, f'Email successfully changed from {old_email} to {self.email}.'
        
    def _clear_email_change_data(self):
        """Helper method to clear all email change related fields"""
        self.new_email = None
        self.email_change_token = None
        self.email_change_token_created = None
        self.email_verification_code = None
        self.email_verification_code_created = None
        self.save()
        
    def _generate_verification_token(self):
        # This method should be implemented to generate a verification token
        pass

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
