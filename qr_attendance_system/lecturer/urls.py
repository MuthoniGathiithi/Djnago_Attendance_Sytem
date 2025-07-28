from django.urls import path
from django.contrib.auth.views import LoginView
from . import views

app_name = 'lecturer'

urlpatterns = [
    # Authentication URLs
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard and Course Management URLs
    path('', views.dashboard, name='dashboard'),
    path('add-course/', views.add_course, name='add_course'),
    path('course/<int:course_id>/generate-qr/', views.generate_qr, name='generate_qr'),

    # Attendance URLs
    path('attendance/<int:course_id>/', views.attendance_view, name='attendance'),
]
