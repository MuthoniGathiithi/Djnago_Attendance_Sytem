from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.crypto import get_random_string
from datetime import timedelta
import qrcode
from .models import Lecturer, Course, Attendance, LoginLog, LoginAttempt
from .forms import LecturerRegistrationForm, CourseForm, QRCodeGenerationForm, ResendVerificationForm, EmailChangeForm
from .utils import (
    send_verification_email, 
    check_rate_limit, 
    log_login_attempt, 
    is_token_valid, 
    generate_verification_token,
    send_email_change_verification
)
from django.conf import settings
import json
import os


def get_client_ip(request):
    """Helper function to get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def login_view(request):
    """View for lecturer login with rate limiting and account lockout"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Get client info for logging and rate limiting
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Check rate limiting for login attempts
        is_blocked, attempts, time_remaining = check_rate_limit(
            f"login_ip_{ip_address}",
            max_attempts=5,  # 5 failed attempts allowed
            window_minutes=15  # 15 minute lockout window
        )
        
        if is_blocked:
            messages.error(
                request,
                f'Too many login attempts. Please try again in {time_remaining} minutes.'
            )
            return redirect('lecturer:login')
        
        # Check if username exists and account is active
        user = None
        try:
            user = Lecturer.objects.get(username=username)
            
            # Check if account is locked due to too many failed attempts
            if user.failed_login_attempts >= 5 and user.last_failed_login:
                time_since_last_attempt = timezone.now() - user.last_failed_login
                if time_since_attempt < timedelta(minutes=15):
                    time_remaining = 15 - (time_since_attempt.seconds // 60)
                    messages.error(
                        request,
                        f'Account temporarily locked due to too many failed attempts. '
                        f'Please try again in {time_remaining} minutes or reset your password.'
                    )
                    return redirect('lecturer:login')
                else:
                    # Reset failed attempts if lockout period has passed
                    user.failed_login_attempts = 0
                    user.save()
            
            # Check if email is verified
            if not user.email_verified:
                messages.warning(
                    request,
                    'Please verify your email address before logging in. '
                    '<a href=\"{}?email={}" class="alert-link">Resend verification email</a>'.format(
                        reverse('lecturer:resend_verification'),
                        user.email
                    ),
                    extra_tags='safe'
                )
                return redirect('lecturer:login')
                
        except Lecturer.DoesNotExist:
            # Don't reveal if username exists or not
            pass
        
        # Authenticate the user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Reset failed login attempts on successful login
            if user.failed_login_attempts > 0:
                user.failed_login_attempts = 0
                user.last_failed_login = None
                user.save()
            
            # Handle "Remember Me" functionality
            remember_me = request.POST.get('remember_me')
            if remember_me:
                # Set session to expire in 30 days
                request.session.set_expiry(30 * 24 * 60 * 60)  # 30 days in seconds
            else:
                # Use default session expiry (browser close)
                request.session.set_expiry(0)
            
            # Log the successful login
            LoginLog.objects.create(
                lecturer=user,
                action='login',
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            login(request, user)
            messages.success(request, 'Login successful!')
            
            # Redirect to next URL if provided, otherwise to dashboard
            next_url = request.GET.get('next', reverse('lecturer:dashboard'))
            return redirect(next_url)
            
        else:
            # Handle failed login attempt
            if user is not None and isinstance(user, Lecturer):
                # Increment failed login attempts
                user.failed_login_attempts += 1
                user.last_failed_login = timezone.now()
                user.save()
                
                # Log the failed login attempt
                LoginLog.objects.create(
                    lecturer=user,
                    action='failed',
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                # Check if account should be locked
                if user.failed_login_attempts >= 5:
                    messages.error(
                        request,
                        'Too many failed login attempts. Your account has been temporarily locked. '
                        'Please try again in 15 minutes or reset your password.'
                    )
                else:
                    attempts_remaining = 5 - user.failed_login_attempts
                    messages.error(
                        request,
                        f'Invalid username or password. {attempts_remaining} attempts remaining.'
                    )
            else:
                # Generic error message to avoid username enumeration
                messages.error(request, 'Invalid username or password.')
            
    return render(request, 'lecturer/login.html', {
        'title': 'Lecturer Login'
    })


def verify_email(request, token):
    """
    Verify user's email using the token sent to their email.
    Handles various verification scenarios with appropriate user feedback.
    """
    try:
        # Find user with this verification token
        user = get_object_or_404(Lecturer, verification_token=token)
        
        # Check if email is already verified
        if user.email_verified:
            messages.info(
                request,
                'This email address has already been verified. You can log in with your credentials.'
            )
            return redirect('lecturer:login')
        
        # Check if token is valid
        if not is_token_valid(user.verification_token_created):
            messages.warning(
                request,
                'This verification link has expired. We\'ve sent a new verification email to your address.'
            )
            # Generate and send a new token
            user.verification_token = generate_verification_token()
            user.verification_token_created = timezone.now()
            user.save()
            send_verification_email(request, user)  # Send new verification email
            return redirect('lecturer:login')
        
        # Mark email as verified and activate account
        user.email_verified = True
        user.verification_token = None  # Clear the token after use
        user.verification_token_created = None
        user.is_active = True  # Activate the user
        user.save()
        
        # Log the email verification
        LoginLog.objects.create(
            lecturer=user,
            action='email_verified',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Send welcome email (optional)
        # send_welcome_email(request, user)
        
        messages.success(
            request,
            '🎉 Your email has been verified successfully! You can now log in to your account.'
        )
        return redirect('lecturer:login')
        
    except Http404:
        messages.error(
            request,
            '❌ Invalid verification link. This could be because: \n'
            '1. The link was copied incorrectly \n'
            '2. The verification link has already been used \n'
            '3. The account no longer exists\n\n'
            'Please try registering again or contact support if the issue persists.'
        )
        return redirect('lecturer:register')
        
    except Exception as e:
        if settings.DEBUG:
            error_msg = str(e)
        else:
            error_msg = 'An unexpected error occurred during email verification.'
            
        messages.error(
            request,
            f'❌ {error_msg} Please try again or contact support if the issue persists.'
        )
        return redirect('lecturer:login')


def resend_verification_email_view(request):
    """
    Resend verification email to the user.
    """
    if request.method == 'POST':
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = Lecturer.objects.get(email=email)
                
                if user.email_verified:
                    messages.info(request, 'Your email is already verified. You can log in.')
                    return redirect('lecturer:login')
                
                # Check rate limiting for verification emails
                ip_address = get_client_ip(request)
                is_blocked, _, _ = check_rate_limit(
                    f"resend_verify_{ip_address}",
                    max_attempts=3,  # Limit to 3 resend attempts per hour
                    window_minutes=60
                )
                
                if is_blocked:
                    messages.error(
                        request,
                        'Too many verification email requests. Please try again later.'
                    )
                    return redirect('lecturer:resend_verification')
                
                # Generate new token
                user.verification_token = generate_verification_token()
                user.verification_token_created = timezone.now()
                user.save()
                
                # Resend verification email
                email_sent, error_message = send_verification_email(request, user)
                if email_sent:
                    messages.success(
                        request,
                        'Verification email has been resent. Please check your inbox. '
                        'The link will expire in 15 minutes.'
                    )
                else:
                    messages.error(
                        request,
                        f'Failed to send verification email. Error: {error_message}. Please try again later.'
                    )
                
                return redirect('lecturer:login')
                
            except Lecturer.DoesNotExist:
                # Don't reveal if email exists or not for security
                messages.success(
                    request,
                    'If an account exists with this email, a verification link has been sent.'
                )
                return redirect('lecturer:login')
    else:
        form = ResendVerificationForm()
    
    return render(request, 'lecturer/resend_verification.html', {
        'form': form,
        'title': 'Resend Verification Email'
    })


def register(request):
    """View for lecturer registration with email verification"""
    if request.method == 'POST':
        form = LecturerRegistrationForm(request.POST)
        if form.is_valid():
            # Check rate limiting for registration attempts
            ip_address = get_client_ip(request)
            is_blocked, attempts, time_until_reset = check_rate_limit(
                f"register_{ip_address}",
                max_attempts=5,  # Limit to 5 registration attempts per hour
                window_minutes=60
            )
            
            if is_blocked:
                messages.error(
                    request,
                    'Too many registration attempts. Please try again later.'
                )
                return redirect('lecturer:register')
            
            # Save the user but don't log them in yet
            user = form.save(commit=False)
            user.is_staff = True  # Ensure lecturer has staff privileges
            user.is_active = False  # User must verify email first
            user.verification_token = generate_verification_token()
            user.verification_token_created = timezone.now()
            user.save()
            
            # Log the registration attempt
            log_login_attempt(ip_address, user.username, successful=True)
            
            # Send verification email
            email_sent, error_message = send_verification_email(request, user)
            if email_sent:
                messages.info(
                    request,
                    'Registration successful! Please check your email to verify your account. '
                    'The verification link will expire in 15 minutes.'
                )
                return redirect('lecturer:login')
            else:
                # If email sending fails, still create the user but notify them
                user.is_active = True  # Activate the account anyway
                user.save()
                messages.warning(
                    request,
                    'Registration successful, but we couldn\'t send a verification email. '
                    f'Error: {error_message}. Please contact support.'
                )
                login(request, user)
                return redirect('lecturer:dashboard')
        else:
            # Log failed registration attempt
            ip_address = get_client_ip(request)
            username = request.POST.get('username')
            log_login_attempt(ip_address, username, successful=False)
            
            messages.error(request, 'Registration failed. Please check the form for errors.')
    else:
        form = LecturerRegistrationForm()
    
    return render(request, 'lecturer/register.html', {
        'form': form,
        'title': 'Lecturer Registration'
    })

from django.http import HttpResponse


@login_required
def dashboard(request):
    """Lecturer dashboard view showing their courses"""
    # Make sure we have a Lecturer instance
    if not hasattr(request.user, 'department'):  # Check if it's a Lecturer
        # If not, create a Lecturer instance from the User
        from django.contrib.auth import get_user_model
        User = get_user_model()
        lecturer = User.objects.get(pk=request.user.pk)
    else:
        lecturer = request.user
        
    courses = Course.objects.filter(lecturer=lecturer)
    return render(request, 'lecturer/dashboard.html', {
        'courses': courses,
        'title': 'Lecturer Dashboard'
    })

#
@login_required
def add_course(request):
    """View for adding a new course"""
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.lecturer = request.user
            course.save()
            messages.success(request, f'Course "{course.title}" has been added successfully.')
            return redirect('lecturer:dashboard')
        else:
            messages.error(request, 'Failed to add course. Please check the form for errors.')
    else:
        form = CourseForm()
    
    return render(request, 'lecturer/add_course.html', {
        'form': form,
        'title': 'Add Course'
    })


@login_required
def generate_qr(request, course_id):
    """Generate QR code for a course"""
    try:
        course = Course.objects.get(id=course_id)
        if not course.lecturer == request.user:
            return JsonResponse({'error': 'You do not have permission to generate QR code for this course'}, status=403)

        # Create QR code data
        qr_data = {
            'course_id': course.id,
            'title': course.title,
            'day': course.day,
            'start_time': course.start_time.strftime('%H:%M'),
            'end_time': course.end_time.strftime('%H:%M'),
            'timestamp': timezone.now().isoformat()
        }

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to media storage
        filename = f'qr_{course.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.png'
        filepath = os.path.join('qr_codes', filename)
        
        # Create BytesIO object
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        # Create File object
        file = File(buffer, name=filename)
        
        # Save to model
        course.qr_code.save(filename, file)
        course.qr_code_url = request.build_absolute_uri(course.qr_code.url)
        course.save()
        
        # Return JSON response
        return JsonResponse({
            'success': True,
            'qr_code_url': course.qr_code_url,
            'message': 'QR code generated successfully'
        })

    except Course.DoesNotExist:
        return JsonResponse({'error': 'Course not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def logout_view(request):
    """Handle user logout"""
    # Log logout before actually logging out
    if request.user.is_authenticated:
        LoginLog.objects.create(
            lecturer=request.user,
            action='logout',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
    
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('lecturer:login')


def attendance_view(request, course_id):
    """View for student attendance submission"""
    try:
        course = Course.objects.get(id=course_id)
        if request.method == 'POST':
            form = AttendanceForm(request.POST, course=course)
            if form.is_valid():
                attendance = form.save()
                messages.success(request, 'Attendance marked successfully!')
                return redirect('lecturer:attendance', course_id=course_id)
        else:
            form = AttendanceForm(course=course)
        
        # Get recent attendance records for this course
        recent_attendance = Attendance.objects.filter(course=course).order_by('-timestamp')[:5]
        
        return render(request, 'lecturer/attendance.html', {
            'form': form,
            'course': course,
            'recent_attendance': recent_attendance,
            'title': f'Attendance - {course.title}'
        })
    except Course.DoesNotExist:
        messages.error(request, 'Course not found')
        return redirect('lecturer:dashboard')
