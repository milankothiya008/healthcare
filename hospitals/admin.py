from django.contrib import admin
from .models import Hospital, HospitalReview

@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'total_beds', 'get_available_beds_display']

@admin.register(HospitalReview)
class HospitalReviewAdmin(admin.ModelAdmin):
    list_display = ['hospital', 'patient', 'rating', 'created_at']
