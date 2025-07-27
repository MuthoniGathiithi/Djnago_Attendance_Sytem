from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .models import Lecturer


class LecturerLoginView(LoginView):
    template_name = 'lecturer/login.html'
    redirect_authenticated_user = True
    extra_context = {'title': 'Lecturer Login'}

    def get_success_url(self):
        return reverse_lazy('lecturer:dashboard')


def register(request):
    """View for lecturer registration"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            lecturer = form.save(commit=False)
            lecturer.is_staff = True
            lecturer.save()
            
            # Login the user after registration
            login(request, lecturer)
            messages.success(request, 'Registration successful! You are now logged in.')
            return redirect('lecturer:dashboard')
        else:
            messages.error(request, 'Registration failed. Please check the form for errors.')
    else:
        form = UserCreationForm()
    
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


def logout_view(request):
    """Logout view for lecturers"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('lecturer:login')
