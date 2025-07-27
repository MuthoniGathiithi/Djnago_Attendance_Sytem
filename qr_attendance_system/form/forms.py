from django import forms

from .models import studentform

class StudentForm(forms.ModelForm):
    class Meta:
        model = studentform
        fields = ['name', 'course', 'admin_no']