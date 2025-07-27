from django.shortcuts import render,redirect
from .forms import StudentForm

def submit_attedance(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('success')  # Redirect to a success page or another view
    else:
        form = StudentForm()
    
    return render(request, 'attendance_form.html', {'form': form})

# Create your views here.
