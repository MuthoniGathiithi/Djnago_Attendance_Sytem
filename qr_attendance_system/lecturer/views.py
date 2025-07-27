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
from django_qrcode import qrcode
from .models import Lecturer, Course, Attendance
from .forms import LecturerRegistrationForm, CourseForm, QRCodeGenerationForm
import json
import os


class LecturerLoginView(LoginView):
    template_name = 'lecturer/login.html'
    redirect_authenticated_user = True
    extra_context = {'title': 'Lecturer Login'}

    def get_success_url(self):
        return reverse_lazy('lecturer:dashboard')


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
        course = Course.objects.get(id=course_id, lecturer=request.user)
        
        # Generate QR code URL
        qr_url = f'/lecturer/attendance/{course_id}/'
        
        # Generate QR code image
        qr = qrcode.make(qr_url)
        qr_filename = f'qr_{course_id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.png'
        qr_path = f'qr_codes/{qr_filename}'
        
        # Save QR code to media storage
        with default_storage.open(qr_path, 'wb') as f:
            qr.save(f)
        
        # Update course with new QR code
        course.qr_code = qr_path
        course.qr_code_url = qr_url
        course.save()
        
        return JsonResponse({
            'success': True,
            'qr_code_url': request.build_absolute_uri(course.qr_code.url),
            'message': 'QR code generated successfully'
        })
    except Course.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Course not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


def logout_view(request):
    """Logout view for lecturers"""
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
