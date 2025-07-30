from django.contrib import admin
from .models import Lecturer, Course, Attendance, LoginLog


@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email', 'department', 'is_active', 'date_joined')
    list_filter = ('department', 'is_active', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    readonly_fields = ('date_joined', 'last_login')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'lecturer', 'day', 'start_time', 'end_time')
    list_filter = ('day', 'lecturer__department')
    search_fields = ('title', 'lecturer__username', 'lecturer__first_name', 'lecturer__last_name')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'student_admin_no', 'course', 'timestamp')
    list_filter = ('course', 'timestamp')
    search_fields = ('student_name', 'student_admin_no', 'course__title')
    readonly_fields = ('timestamp',)


@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    list_display = ('lecturer', 'action', 'timestamp', 'ip_address')
    list_filter = ('action', 'timestamp', 'lecturer__department')
    search_fields = ('lecturer__username', 'lecturer__first_name', 'lecturer__last_name', 'ip_address')
    readonly_fields = ('lecturer', 'action', 'timestamp', 'ip_address', 'user_agent')
    
    def has_add_permission(self, request):
        return False  # Prevent manual creation of login logs
    
    def has_change_permission(self, request, obj=None):
        return False  # Prevent editing of login logs
