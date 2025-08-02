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
from .models import LoginLog, LoginAttempt


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


from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

def send_verification_email(request, lecturer):
    """
    Send email verification email to lecturer with verification code.
    Returns (success: bool, error_message: str)
    """
    try:
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
        verification_url = f"https://{current_site.domain}{reverse('lecturer:verify_email', kwargs={'token': token})}"
        
        # Prepare email context
        context = {
            'lecturer': lecturer,
            'verification_code': verification_code,
            'verification_url': verification_url,
            'current_site': current_site,
        }
        
        # Render email content
        subject = 'Verify Your Email - QR Attendance System'
        text_content = f"""
        Dear {lecturer.first_name} {lecturer.last_name},
        
        Thank you for registering with the QR Attendance System!
        
        Your verification code is: {verification_code}
        
        Or visit this link to verify your email address:
        {verification_url}
        
        This code will expire in 15 minutes.
        
        If you didn't create this account, please ignore this email.
        
        Best regards,
        QR Attendance System Team
        """
        
        # Render HTML content from template
        html_content = render_to_string('lecturer/emails/verification_email.html', context)
        
        # Create email message
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[lecturer.email],
            reply_to=[settings.DEFAULT_FROM_EMAIL],
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send email with timeout
        email.send(fail_silently=False)
        
        # Log successful email sending
        if settings.DEBUG:
            print(f"Verification email sent to {lecturer.email}")
            
        return True, None
        
    except Exception as e:
        error_msg = f"Failed to send verification email: {str(e)}"
        if settings.DEBUG:
            print(error_msg)
        return False, error_msg


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
    return LoginAttempt.objects.filter(timestamp__lt=cutoff_date).delete()


def send_email_change_verification(request, lecturer):
    """
    Send email change verification email to the new email address.
    Returns (success: bool, error_message: str)
    """
    try:
        if not lecturer.new_email or not lecturer.email_change_token:
            return False, 'No pending email change found.'
        
        current_site = get_current_site(request)
        verification_url = request.build_absolute_uri(
            reverse('lecturer:confirm_email_change', 
                   kwargs={'token': lecturer.email_change_token})
        )
        
        # Prepare email context
        context = {
            'user': lecturer,
            'verification_url': verification_url,
            'site_name': current_site.name,
            'expiry_hours': '24',  # Matches the token expiration in the model
        }
        
        # Render email content
        subject = 'Confirm Your New Email Address'
        text_content = render_to_string(
            'lecturer/emails/email_change_verification.txt',
            context
        )
        html_content = render_to_string(
            'lecturer/emails/email_change_verification.html',
            context
        )
        
        # Send email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[lecturer.new_email],
            reply_to=[settings.DEFAULT_FROM_EMAIL]
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        # Send notification to old email (optional)
        # send_email_change_notification(lecturer, lecturer.email)
        
        return True, ''
        
    except Exception as e:
        if settings.DEBUG:
            error_msg = str(e)
        else:
            error_msg = 'Failed to send verification email.'
        return False, error_msg[0]
