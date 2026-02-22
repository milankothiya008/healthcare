from django.db import models
from django.conf import settings
from django.utils import timezone


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
    facilities = models.TextField(blank=True, help_text="Departments - comma separated")
    total_beds = models.PositiveIntegerField(default=0)
    available_beds = models.PositiveIntegerField(default=0)  # Kept for migration; use available_beds_count for dynamic
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
        """Get total number of doctors (from assignments + legacy single hospital)"""
        from doctors.models import DoctorProfile
        return DoctorProfile.objects.filter(
            models.Q(hospital_assignments__hospital=self, hospital_assignments__is_active=True) |
            models.Q(hospital=self)
        ).distinct().count()

    def get_doctors(self):
        """Queryset of doctors at this hospital (assignments or legacy hospital FK)"""
        from doctors.models import DoctorProfile
        return DoctorProfile.objects.filter(
            models.Q(hospital_assignments__hospital=self, hospital_assignments__is_active=True) |
            models.Q(hospital=self)
        ).distinct()

    @property
    def occupied_beds_count(self):
        """Count of beds occupied by active admissions: already started and not yet discharged.
        Discharge automatically frees the bed (discharge_time set)."""
        from django.db.models import Q
        now = timezone.now()
        return self.admissions.filter(
            admission_time__lte=now
        ).filter(
            Q(discharge_time__isnull=True) | Q(discharge_time__gt=now)
        ).count()

    @property
    def available_beds_count(self):
        """Dynamically calculated: total_beds - occupied (do not edit; set total_beds only)"""
        return max(0, self.total_beds - self.occupied_beds_count)

    def get_available_beds_display(self):
        """For admin list_display (avoids property in admin)"""
        return self.available_beds_count

    get_available_beds_display.short_description = 'Available beds'

    @property
    def average_rating(self):
        """Calculate average rating from reviews"""
        from django.db.models import Avg
        result = self.reviews.aggregate(avg=Avg('rating'))
        return round(result['avg'] or 0, 1)


class HospitalReview(models.Model):
    """Review for hospital - patient can review only after completed appointment"""
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hospital_reviews',
        limit_choices_to={'role': 'PATIENT'}
    )
    rating = models.PositiveSmallIntegerField()  # 1-5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'hospital_reviews'
        verbose_name = 'Hospital Review'
        verbose_name_plural = 'Hospital Reviews'
        unique_together = ('hospital', 'patient')

    def __str__(self):
        return f"Review by {self.patient.username} for {self.hospital.name}"


class DoctorHospitalRequest(models.Model):
    """Doctor work request to hospital - with expected monthly salary; no negotiation"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    doctor = models.ForeignKey(
        'doctors.DoctorProfile',
        on_delete=models.CASCADE,
        related_name='hospital_requests'
    )
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='doctor_requests'
    )
    expected_monthly_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Expected salary when sending request")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'doctor_hospital_requests'
        verbose_name = 'Doctor Hospital Request'
        verbose_name_plural = 'Doctor Hospital Requests'
        unique_together = ('doctor', 'hospital')

    def __str__(self):
        return f"{self.doctor} -> {self.hospital} ({self.status})"


class DoctorHospitalAssignment(models.Model):
    """Doctor assigned to hospital (multi-hospital); salary fixed at approval"""
    doctor = models.ForeignKey(
        'doctors.DoctorProfile',
        on_delete=models.CASCADE,
        related_name='hospital_assignments'
    )
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='doctor_assignments'
    )
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'doctor_hospital_assignments'
        verbose_name = 'Doctor Hospital Assignment'
        verbose_name_plural = 'Doctor Hospital Assignments'
        unique_together = ('doctor', 'hospital')

    def __str__(self):
        return f"{self.doctor} at {self.hospital}"


class Admission(models.Model):
    """Patient admission - bed occupancy is time-based"""
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admissions',
        limit_choices_to={'role': 'PATIENT'}
    )
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name='admissions'
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admissions_attended',
        limit_choices_to={'role': 'DOCTOR'}
    )
    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admissions'
    )
    admission_time = models.DateTimeField()
    expected_discharge_time = models.DateTimeField(null=True, blank=True)
    discharge_time = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admissions'
        verbose_name = 'Admission'
        verbose_name_plural = 'Admissions'
        ordering = ['-admission_time']

    def __str__(self):
        return f"{self.patient} at {self.hospital} from {self.admission_time}"

    @property
    def is_active(self):
        """Admission is active if not yet discharged or discharge is in future"""
        if self.discharge_time is None:
            return True
        return self.discharge_time > timezone.now()

    @property
    def duration_of_stay(self):
        """Duration in hours if discharged"""
        if not self.discharge_time:
            return None
        delta = self.discharge_time - self.admission_time
        return round(delta.total_seconds() / 3600, 1)
