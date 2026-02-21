from django.db import models
from django.conf import settings


class Appointment(models.Model):
    """Appointment model connecting Patients, Doctors, and Hospitals"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
        ('RESCHEDULED', 'Rescheduled'),
    ]
    
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_appointments',
        limit_choices_to={'role': 'PATIENT'}
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='doctor_appointments',
        limit_choices_to={'role': 'DOCTOR'}
    )
    hospital = models.ForeignKey(
        'hospitals.Hospital',
        on_delete=models.CASCADE,
        related_name='appointments',
        null=True,
        blank=True
    )
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    reason = models.TextField(help_text="Reason for appointment")
    notes = models.TextField(blank=True, help_text="Additional notes")
    prescription = models.TextField(blank=True, help_text="Prescription details")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'appointments'
        verbose_name = 'Appointment'
        verbose_name_plural = 'Appointments'
        ordering = ['-appointment_date', '-appointment_time']
    
    def __str__(self):
        return f"Appointment: {self.patient.username} with Dr. {self.doctor.username} on {self.appointment_date}"
    
    def can_be_cancelled(self):
        """Check if appointment can be cancelled"""
        return self.status in ['PENDING', 'CONFIRMED']
    
    def can_be_rescheduled(self):
        """Check if appointment can be rescheduled"""
        return self.status in ['PENDING', 'CONFIRMED']
