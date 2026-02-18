from django.db import models
from django.conf import settings

class DoctorProfile(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    specialization = models.CharField(max_length=100)
    experience_years = models.IntegerField()
    phone = models.CharField(max_length=15)
    hospital_name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    profile_photo = models.ImageField(upload_to='doctor_photos/', null=True, blank=True)
    def __str__(self):
        return self.user.email
