from django.test import TestCase, Client
from django.urls import reverse

from .models import User


class DoctorDashboardPermissionTests(TestCase):
    """Ensure only DOCTOR role can access doctor dashboard; Hospital Admin must get 403 or redirect."""

    def setUp(self):
        self.client = Client()

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(reverse('accounts:doctor_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_hospital_admin_cannot_access_doctor_dashboard(self):
        """Login as Hospital Admin, open /accounts/doctor/dashboard/ -> must NOT return 200 (403 or redirect)."""
        hospital_user = User.objects.create_user(
            username='hospital1',
            email='hospital@test.com',
            password='pass',
            role='HOSPITAL',
            is_approved=True,
        )
        self.client.force_login(hospital_user)
        response = self.client.get(reverse('accounts:doctor_dashboard'))
        self.assertIn(response.status_code, (302, 403), 'Hospital Admin must not get 200 on doctor dashboard')
        if response.status_code == 302:
            self.assertTrue(response.url.startswith('/accounts/'))

    def test_doctor_can_access_doctor_dashboard(self):
        """Approved doctor can access dashboard."""
        doctor_user = User.objects.create_user(
            username='doctor1',
            email='doctor@test.com',
            password='pass',
            role='DOCTOR',
            is_approved=True,
        )
        from doctors.models import DoctorProfile
        DoctorProfile.objects.create(user=doctor_user, license_number='L1', qualification='MBBS', specialization='GENERAL')
        self.client.force_login(doctor_user)
        response = self.client.get(reverse('accounts:doctor_dashboard'))
        self.assertEqual(response.status_code, 200)
