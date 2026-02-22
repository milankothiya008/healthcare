from django.db import models
from django.conf import settings
from datetime import time


class DoctorProfile(models.Model):
    """Doctor profile extending User model"""
    
    SPECIALIZATION_CHOICES = [
        ('CARDIOLOGY', 'Cardiology'),
        ('DERMATOLOGY', 'Dermatology'),
        ('NEUROLOGY', 'Neurology'),
        ('ORTHOPEDICS', 'Orthopedics'),
        ('PEDIATRICS', 'Pediatrics'),
        ('PSYCHIATRY', 'Psychiatry'),
        ('SURGERY', 'Surgery'),
        ('GENERAL', 'General Medicine'),
        ('ONCOLOGY', 'Oncology'),
        ('GYNECOLOGY', 'Gynecology'),
    ]
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='doctor_profile'
    )
    license_number = models.CharField(max_length=50, unique=True)
    specialization = models.CharField(max_length=50, choices=SPECIALIZATION_CHOICES, default='GENERAL')
    years_of_experience = models.PositiveIntegerField(default=0)
    qualification = models.CharField(max_length=200)
    bio = models.TextField(blank=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    profile_picture = models.ImageField(upload_to='doctor_profiles/', blank=True, null=True)
    verification_document = models.FileField(upload_to='doctor_verifications/', blank=True, null=True, help_text="Upload license or certification document for verification")
    hospital = models.ForeignKey(
        'hospitals.Hospital',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='doctors'
    )
    is_available = models.BooleanField(default=True)
    available_from = models.TimeField(default=time(9, 0), help_text="Start of working hours")
    available_to = models.TimeField(default=time(17, 0), help_text="End of working hours")
    slot_duration_minutes = models.PositiveIntegerField(default=30)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'doctor_profiles'
        verbose_name = 'Doctor Profile'
        verbose_name_plural = 'Doctor Profiles'
    
    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username} - {self.get_specialization_display()}"


class DoctorProfileUpdateRequest(models.Model):
    """Sensitive profile changes require System Admin approval"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    FIELD_CHOICES = [
        ('specialization', 'Specialization'),
        ('qualification', 'Qualification'),
        ('license_number', 'License Number'),
        ('verification_document', 'Verification Document'),
    ]
    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='profile_update_requests'
    )
    field_name = models.CharField(max_length=50, choices=FIELD_CHOICES)
    new_value_text = models.CharField(max_length=500, blank=True)
    new_value_file = models.FileField(upload_to='doctor_update_requests/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_doctor_updates'
    )

    class Meta:
        db_table = 'doctor_profile_update_requests'
        verbose_name = 'Doctor Profile Update Request'
        verbose_name_plural = 'Doctor Profile Update Requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.doctor} - {self.get_field_name_display()} ({self.status})"


class DoctorLeave(models.Model):
    """Blocked dates for doctor leave; no appointments bookable"""
    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='leave_dates'
    )
    leave_date = models.DateField()

    class Meta:
        db_table = 'doctor_leave'
        verbose_name = 'Doctor Leave'
        verbose_name_plural = 'Doctor Leave'
        unique_together = ('doctor', 'leave_date')
        ordering = ['leave_date']

    def __str__(self):
        return f"{self.doctor} - {self.leave_date}"
