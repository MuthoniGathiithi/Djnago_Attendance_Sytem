release: python qr_attendance_system/manage.py migrate
web: gunicorn qr_attendance_system.qr_attendance_system.wsgi:application --bind 0.0.0.0:$PORT
