import secrets
import string
import random
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.conf import settings
from django.core.cache import cache
from .models import LoginLog


def generate_verification_token():
    """Generate a secure random token for email verification"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))


def generate_verification_code():
    """Generate a 6-digit verification code"""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])


def is_verification_code_valid(code_created_time, expiry_minutes=15):
    """Check if verification code is still valid (not expired)"""
    if not code_created_time:
        return False
    
    expiry_time = code_created_time + timedelta(minutes=expiry_minutes)
    return timezone.now() < expiry_time


def send_verification_email(request, lecturer):
    """Send email verification email to lecturer with verification code"""
    # Generate verification token and code
    token = generate_verification_token()
    verification_code = generate_verification_code()
    
    # Save verification details
    lecturer.verification_token = token
    lecturer.verification_token_created = timezone.now()
    lecturer.verification_code = verification_code
    lecturer.verification_code_created = timezone.now()
    lecturer.save()
    
    # Build verification URL
    current_site = get_current_site(request)
    verification_url = f"http://{current_site.domain}{reverse('lecturer:verify_email', kwargs={'token': token})}"
    
    # Email content
    subject = 'Verify Your Email - QR Attendance System'
    message = f"""
    Dear {lecturer.first_name} {lecturer.last_name},
    
    Thank you for registering with the QR Attendance System!
    
    Your verification code is: {verification_code}
    
    Or click the link below to verify your email address:
    {verification_url}
    
    This code will expire in 15 minutes.
    
    If you didn't create this account, please ignore this email.
    
    Best regards,
    QR Attendance System Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [lecturer.email],
            fail_silently=False,
            html_message=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>Verify Your Email</h2>
                <p>Dear {lecturer.first_name} {lecturer.last_name},</p>
                <p>Thank you for registering with the QR Attendance System!</p>
                
                <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; text-align: center; margin: 20px 0;">
                    <h3 style="margin: 0; color: #333; font-size: 24px; letter-spacing: 2px;">
                        {verification_code}
                    </h3>
                    <p style="color: #666; margin: 10px 0 0;">This code will expire in 15 minutes</p>
                </div>
                
                <p>Or click the button below to verify your email:</p>
                <a href="{verification_url}" 
                   style="display: inline-block; background: #4CAF50; color: white; 
                          padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    Verify Email
                </a>
                
                <p style="margin-top: 30px; font-size: 12px; color: #666;">
                    If you didn't create this account, please ignore this email.
                </p>
                
                <p>Best regards,<br>QR Attendance System Team</p>
            </div>
            """
        )
        return True
    except Exception as e:
        print(f"Failed to send verification email: {e}")
        return False


def is_token_valid(lecturer):
    """Check if verification token is still valid (24 hours)"""
    if not lecturer.verification_token_created:
        return False
    
    expiry_time = lecturer.verification_token_created + timedelta(hours=24)
    return timezone.now() < expiry_time


def check_rate_limit(ip_address, username=None, max_attempts=5, window_minutes=15):
    """
    Check if IP address or username has exceeded login attempt rate limit
    Returns (is_blocked, attempts_count, time_until_reset)
    """
    cutoff_time = timezone.now() - timedelta(minutes=window_minutes)
    
    # Count failed attempts from this IP in the time window
    ip_attempts = LoginAttempt.objects.filter(
        ip_address=ip_address,
        timestamp__gte=cutoff_time,
        successful=False
    ).count()
    
    username_attempts = 0
    if username:
        # Count failed attempts for this username in the time window
        username_attempts = LoginAttempt.objects.filter(
            username=username,
            timestamp__gte=cutoff_time,
            successful=False
        ).count()
    
    total_attempts = max(ip_attempts, username_attempts)
    is_blocked = total_attempts >= max_attempts
    
    # Calculate time until reset
    time_until_reset = None
    if is_blocked:
        oldest_attempt = LoginAttempt.objects.filter(
            ip_address=ip_address,
            timestamp__gte=cutoff_time,
            successful=False
        ).order_by('timestamp').first()
        
        if oldest_attempt:
            reset_time = oldest_attempt.timestamp + timedelta(minutes=window_minutes)
            time_until_reset = reset_time - timezone.now()
    
    return is_blocked, total_attempts, time_until_reset


def log_login_attempt(ip_address, username=None, successful=False):
    """Log a login attempt for rate limiting purposes"""
    LoginAttempt.objects.create(
        ip_address=ip_address,
        username=username,
        successful=successful
    )


def cleanup_old_login_attempts(days=7):
    """Clean up old login attempts (run this periodically)"""
    cutoff_date = timezone.now() - timedelta(days=days)
    deleted_count = LoginAttempt.objects.filter(timestamp__lt=cutoff_date).delete()[0]
    return deleted_count
