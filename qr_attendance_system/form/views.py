from django.shortcuts import render, redirect
from .forms import SForm  # Import your actual form

def student_form_view(request):  # Use a lowercase function name
    class_title = request.GET.get('class_title', 'Unknown Class')

    if request.method == 'POST':
        form = SForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'form/success.html', {'class_title': class_title})
    else:
        form = SForm()

    return render(request, 'form/attendance_form.html', {
        'form': form,
        'class_title': class_title
    })
# qr_attendance_system/form/views.py
