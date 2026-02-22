from django.contrib import admin
from .models import Hospital, HospitalReview, DoctorHospitalRequest, DoctorHospitalAssignment

@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'total_beds', 'get_available_beds_display']

@admin.register(HospitalReview)
class HospitalReviewAdmin(admin.ModelAdmin):
    list_display = ['hospital', 'patient', 'rating', 'created_at']


@admin.register(DoctorHospitalRequest)
class DoctorHospitalRequestAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'hospital', 'expected_monthly_salary', 'status', 'created_at']


@admin.register(DoctorHospitalAssignment)
class DoctorHospitalAssignmentAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'hospital', 'monthly_salary', 'is_active', 'joined_at']
