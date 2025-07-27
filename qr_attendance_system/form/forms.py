from django import forms

from .models import Studentform

class SForm(forms.ModelForm):
    class Meta:
        model = Studentform
        fields = ['name', 'course', 'admin_no']