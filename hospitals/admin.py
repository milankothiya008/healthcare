from django.contrib import admin
from .models import Hospital, HospitalReview

@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'available_beds', 'total_beds']

@admin.register(HospitalReview)
class HospitalReviewAdmin(admin.ModelAdmin):
    list_display = ['hospital', 'patient', 'rating', 'created_at']
