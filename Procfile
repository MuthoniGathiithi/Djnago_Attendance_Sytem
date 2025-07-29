release: cd qr_attendance_system && python manage.py migrate
web: cd qr_attendance_system && python -m gunicorn qr_attendance_system.wsgi:application --bind 0.0.0.0:$PORT
