from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from accounts.models import User
from doctors.models import DoctorProfile
from hospitals.models import Hospital, DoctorHospitalAssignment
from .models import Appointment


class BookingValidationTests(TestCase):
    """Past date/time must be rejected at validation level."""

    def setUp(self):
        self.client = Client()
        self.patient = User.objects.create_user(
            username='pat', email='pat@test.com', password='pass',
            role='PATIENT', is_approved=True,
        )
        self.doctor_user = User.objects.create_user(
            username='doc', email='doc@test.com', password='pass',
            role='DOCTOR', is_approved=True,
        )
        self.hosp_user = User.objects.create_user(
            username='h', email='h@test.com', password='pass',
            role='HOSPITAL', is_approved=True,
        )
        self.hospital = Hospital.objects.create(
            name='H', registration_number='REG1', user=self.hosp_user,
        )
        self.doctor = DoctorProfile.objects.create(
            user=self.doctor_user, license_number='L1', qualification='MBBS',
            specialization='GENERAL', hospital=self.hospital,
        )

    def test_booking_past_date_rejected(self):
        """Booking for a date earlier than today must be rejected."""
        self.client.force_login(self.patient)
        yesterday = (timezone.now().date() - timedelta(days=1)).strftime('%Y-%m-%d')
        count_before = Appointment.objects.filter(patient=self.patient).count()
        response = self.client.post(reverse('appointments:book_normal', kwargs={'doctor_id': self.doctor.pk}), data={
            'hospital_id': self.hospital.pk,
            'date': yesterday,
            'time': '10:00',
            'reason': 'Checkup',
        })
        self.assertEqual(Appointment.objects.filter(patient=self.patient).count(), count_before)
        self.assertIn(response.status_code, (302, 200))

    def test_booking_today_past_time_rejected(self):
        """Booking for today at a time that has already passed must be rejected."""
        self.client.force_login(self.patient)
        today = timezone.now().date().strftime('%Y-%m-%d')
        count_before = Appointment.objects.filter(patient=self.patient).count()
        response = self.client.post(reverse('appointments:book_normal', kwargs={'doctor_id': self.doctor.pk}), data={
            'hospital_id': self.hospital.pk,
            'date': today,
            'time': '00:00',
            'reason': 'Checkup',
        })
        self.assertEqual(Appointment.objects.filter(patient=self.patient).count(), count_before)
