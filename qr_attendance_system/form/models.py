from django.shortcuts import render, redirect


def submit_attendance(request):
    class_title = request.GET.get('class_title', 'Unknown Class')  # default fallback

    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'form/success.html', {'class_title': class_title})
    else:
        form = StudentForm()

    return render(request, 'form/attendance_form.html', {
        'form': form,
        'class_title': class_title
    })

