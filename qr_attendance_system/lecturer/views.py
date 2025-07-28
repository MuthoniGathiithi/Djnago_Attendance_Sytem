from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import qrcode
from .models import Lecturer, Course, Attendance
from .forms import LecturerRegistrationForm, CourseForm, QRCodeGenerationForm
import json
import os


def login_view(request):
    """View for lecturer login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, 'Login successful!')
            return redirect('lecturer:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
            
    return render(request, 'lecturer/login.html', {
        'title': 'Lecturer Login'
    })


def register(request):
    """View for lecturer registration"""
    if request.method == 'POST':
        form = LecturerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! You are now logged in.')
            return redirect('lecturer:dashboard')
        else:
            messages.error(request, 'Registration failed. Please check the form for errors.')
    else:
        form = LecturerRegistrationForm()
    
    return render(request, 'lecturer/register.html', {
        'form': form,
        'title': 'Lecturer Registration'
    })


@login_required
def dashboard(request):
    """Lecturer dashboard view showing their courses"""
    courses = request.user.courses.all()
    return render(request, 'lecturer/dashboard.html', {
        'courses': courses,
        'title': 'Lecturer Dashboard'
    })


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
