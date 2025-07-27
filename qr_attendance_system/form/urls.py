from django.urls import path
from . import views

urlpatterns = [
    path('submit_attendance/', views.submit_attendance, name='submit_attendance'),
]
