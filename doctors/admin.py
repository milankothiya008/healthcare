from django.contrib import admin
from .models import DoctorProfile, DoctorProfileUpdateRequest, DoctorLeave


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'specialization', 'license_number', 'hospital', 'is_available']


@admin.register(DoctorProfileUpdateRequest)
class DoctorProfileUpdateRequestAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'field_name', 'status', 'created_at', 'reviewed_at']


@admin.register(DoctorLeave)
class DoctorLeaveAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'leave_date']
