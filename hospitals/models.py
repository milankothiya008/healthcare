from django.db import models
from django.conf import settings


class Hospital(models.Model):
    """Hospital model"""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hospital_profile'
    )
    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    facilities = models.TextField(blank=True)  # Comma-separated or JSON
    total_beds = models.PositiveIntegerField(default=0)
    available_beds = models.PositiveIntegerField(default=0)
    logo = models.ImageField(upload_to='hospital_logos/', blank=True, null=True)
    verification_document = models.FileField(upload_to='hospital_verifications/', blank=True, null=True, help_text="Upload registration certificate or license for verification")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hospitals'
        verbose_name = 'Hospital'
        verbose_name_plural = 'Hospitals'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def total_doctors(self):
        """Get total number of doctors in this hospital"""
        return self.doctors.count()
