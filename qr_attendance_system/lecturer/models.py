from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class Lecturer(AbstractUser):
    """Custom User model for lecturers"""
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    department = models.CharField(max_length=100)
    
    class Meta:
        verbose_name = 'Lecturer'
        verbose_name_plural = 'Lecturers'
        
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"

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
