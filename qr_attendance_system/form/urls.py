from django.urls import path
from . import views

urlpatterns = [
    path('student_form/', views.student_form_view, name='student_form'),
]
# qr_attendance_system/form/urls.py
# This file defines the URL patterns for the form app, mapping the student form view to a
