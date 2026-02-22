from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom User model with role-based access control"""
    
    # Override email to be unique for email-based login
    email = models.EmailField(unique=True)
    
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('DOCTOR', 'Doctor'),
        ('PATIENT', 'Patient'),
        ('HOSPITAL', 'Hospital'),
        ('HOSPITAL_ADMIN', 'Hospital Admin'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='PATIENT')
    is_approved = models.BooleanField(default=False)  # For Doctor and Hospital approval
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='user_profiles/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_admin(self):
        return self.role == 'ADMIN'
    
    def is_doctor(self):
        return self.role == 'DOCTOR'
    
    def is_patient(self):
        return self.role == 'PATIENT'
    
    def is_hospital(self):
        return self.role == 'HOSPITAL'

    def is_hospital_admin(self):
        return self.role in ('HOSPITAL', 'HOSPITAL_ADMIN')
    
    def can_access_dashboard(self):
        """Check if user can access their dashboard"""
        if self.is_admin():
            return True
        if self.is_doctor() or self.is_hospital():
            return self.is_approved
        if self.is_patient():
            return True
        return False
