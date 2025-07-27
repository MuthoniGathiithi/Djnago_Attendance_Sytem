from django.urls import path
from . import views

urlpatterns = [
   path('submit_attendance/', views.submit_attendance, name='submit_attendance'),
    
]
# qr_attendance_system/form/urls.py
# This file defines the URL patterns for the form app, mapping the student form view to a
