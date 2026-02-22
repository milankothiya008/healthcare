from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from .models import DoctorProfile
from hospitals.models import Hospital
from appointments.models import Appointment


class DoctorSelfOnlySecurityTests(TestCase):
    """Doctor must only access own data; accessing another doctor's appointment must 404."""

    def setUp(self):
        self.client = Client()

    def test_doctor_cannot_access_another_doctors_appointment_detail(self):
        """When logged in as Doctor A, opening Doctor B's appointment detail must return 404 (not 200)."""
        doctor_a_user = User.objects.create_user(
            username='doctor_a', email='doctor_a@test.com', password='pass',
            role='DOCTOR', is_approved=True,
        )
        doctor_b_user = User.objects.create_user(
            username='doctor_b', email='doctor_b@test.com', password='pass',
            role='DOCTOR', is_approved=True,
        )
        profile_a = DoctorProfile.objects.create(
            user=doctor_a_user, license_number='L1', qualification='MBBS', specialization='GENERAL',
        )
        profile_b = DoctorProfile.objects.create(
            user=doctor_b_user, license_number='L2', qualification='MD', specialization='GENERAL',
        )
        patient_user = User.objects.create_user(
            username='patient1', email='patient@test.com', password='pass',
            role='PATIENT', is_approved=True,
        )
        # Appointment belongs to Doctor B (and patient)
        apt = Appointment.objects.create(
            patient=patient_user,
            doctor=doctor_b_user,
            appointment_date='2025-03-01',
            appointment_time='10:00:00',
            reason='Checkup',
            status='PENDING',
        )
        # Log in as Doctor A and try to open Doctor B's appointment detail
        self.client.force_login(doctor_a_user)
        response = self.client.get(reverse('doctors:doctor_appointment_detail', kwargs={'pk': apt.pk}))
        self.assertEqual(response.status_code, 404, 'Doctor A must not access Doctor B\'s appointment (expect 404)')

    def test_doctor_can_access_own_appointment_detail(self):
        """Doctor can access their own appointment."""
        doctor_user = User.objects.create_user(
            username='doctor1', email='d@test.com', password='pass',
            role='DOCTOR', is_approved=True,
        )
        DoctorProfile.objects.create(
            user=doctor_user, license_number='L1', qualification='MBBS', specialization='GENERAL',
        )
        patient_user = User.objects.create_user(
            username='p1', email='p@test.com', password='pass', role='PATIENT', is_approved=True,
        )
        apt = Appointment.objects.create(
            patient=patient_user, doctor=doctor_user,
            appointment_date='2025-03-01', appointment_time='10:00:00',
            reason='Checkup', status='PENDING',
        )
        self.client.force_login(doctor_user)
        response = self.client.get(reverse('doctors:doctor_appointment_detail', kwargs={'pk': apt.pk}))
        self.assertEqual(response.status_code, 200)

    def test_doctor_cannot_approve_another_doctors_appointment(self):
        """Doctor A must not be able to approve Doctor B's appointment (404)."""
        doctor_a = User.objects.create_user(
            username='dra', email='dra@test.com', password='pass', role='DOCTOR', is_approved=True,
        )
        doctor_b = User.objects.create_user(
            username='drb', email='drb@test.com', password='pass', role='DOCTOR', is_approved=True,
        )
        DoctorProfile.objects.create(user=doctor_a, license_number='LA', qualification='MBBS', specialization='GENERAL')
        DoctorProfile.objects.create(user=doctor_b, license_number='LB', qualification='MBBS', specialization='GENERAL')
        patient = User.objects.create_user(
            username='pat', email='pat@test.com', password='pass', role='PATIENT', is_approved=True,
        )
        apt_b = Appointment.objects.create(
            patient=patient, doctor=doctor_b,
            appointment_date='2025-03-01', appointment_time='10:00:00', reason='Visit', status='PENDING',
        )
        self.client.force_login(doctor_a)
        response = self.client.post(reverse('doctors:doctor_appointment_approve', kwargs={'pk': apt_b.pk}))
        self.assertEqual(response.status_code, 404)


class SlotConflictGlobalTests(TestCase):
    """Slot availability is global: same time booked in one hospital must be unavailable in another."""

    def test_booked_slot_excluded_globally(self):
        """When doctor has 10 AM booked at Hospital A, 10 AM must not appear in available slots (any hospital)."""
        from datetime import time, timedelta
        from django.utils import timezone

        doctor_user = User.objects.create_user(
            username='doc', email='doc@test.com', password='pass',
            role='DOCTOR', is_approved=True,
        )
        hospital_admin_user = User.objects.create_user(
            username='hospadmin', email='hosp@test.com', password='pass',
            role='HOSPITAL', is_approved=True,
        )
        hospital_a = Hospital.objects.create(
            name='Hospital A', registration_number='REG-A', user=hospital_admin_user,
        )
        profile = DoctorProfile.objects.create(
            user=doctor_user, license_number='L1', qualification='MBBS', specialization='GENERAL',
            hospital=hospital_a,
            available_from=time(9, 0), available_to=time(12, 0), slot_duration_minutes=30,
        )
        patient_user = User.objects.create_user(
            username='pat', email='pat@test.com', password='pass', role='PATIENT', is_approved=True,
        )
        # Book 10:00 at Hospital A
        appointment_date = timezone.now().date() + timedelta(days=1)
        Appointment.objects.create(
            patient=patient_user, doctor=doctor_user, hospital=hospital_a,
            appointment_date=appointment_date, appointment_time=time(10, 0),
            reason='Visit', status='CONFIRMED',
        )
        # Compute available slots (same logic as DoctorDetailView._get_available_slots)
        from .views import DoctorDetailView
        view = DoctorDetailView()
        view.object = profile
        slots = view._get_available_slots(profile, appointment_date)
        self.assertNotIn(time(10, 0), slots, '10 AM must be excluded globally once booked at any hospital')
