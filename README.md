# Django Authentication System

A working and complete authentication system built with Django, developed as part of the `qr_attendance_system` project.

## 🔐 Features

- User registration
- User login/logout
- Secure password hashing
- Session-based authentication
- Built-in Django user model
- Environment-aware settings (for both development and production)
- Render-compatible deployment configuration

## 📁 Project Structure

qr_attendance_system/
├── manage.py
├── your_app_name/
│ ├── models.py
│ ├── views.py
│ ├── urls.py
│ └── ...
├── requirements.txt
├── Procfile
├── render.yaml
└── ...

less
Copy code

## 🚀 Deployment

This project is configured for deployment on [Render](https://render.com). Key files:

- **`Procfile`**: Specifies the command to run the Django app.
- **`render.yaml`**: Defines the Render service configuration.
- **`.env` file (optional)**: Used for development environments. Not required in production.

> Note: The project gracefully handles missing `.env` files in production using an optional `dotenv` import.

## 📦 Requirements

Install the required packages:

```bash
pip install -r requirements.txt
