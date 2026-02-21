from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LogoutView
from django.contrib import messages
from django.views.generic import CreateView, TemplateView, ListView, DetailView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import uuid

from .forms import UserRegistrationForm, LoginForm
from .mixins import (
    AdminRequiredMixin, DoctorRequiredMixin, 
    PatientRequiredMixin, HospitalRequiredMixin
)
from .models import User
from patients.models import PatientProfile
from doctors.models import DoctorProfile
from hospitals.models import Hospital
from appointments.models import Appointment
from documents.models import Document


class RegisterView(CreateView):
    """User registration view"""
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')
    
    def form_valid(self, form):
        user = form.save(commit=False)
        
        # Handle profile picture upload
        if 'profile_picture' in self.request.FILES:
            user.profile_picture = self.request.FILES['profile_picture']
        
        user.save()
        
        # Handle verification document and create profile based on role
        if user.role == 'PATIENT':
            PatientProfile.objects.create(user=user)
        elif user.role == 'DOCTOR':
            # Generate unique license number
            license_num = f"LIC-{uuid.uuid4().hex[:8].upper()}"
            doctor_profile = DoctorProfile.objects.create(
                user=user,
                license_number=license_num,
                specialization='GENERAL',  # Default specialization
                qualification="Pending"  # Will be updated later
            )
            # Handle verification document for doctor
            if 'verification_document' in self.request.FILES:
                doctor_profile.verification_document = self.request.FILES['verification_document']
                doctor_profile.save()
        elif user.role == 'HOSPITAL':
            # Generate unique registration number
            reg_num = f"REG-{uuid.uuid4().hex[:8].upper()}"
            hospital = Hospital.objects.create(
                user=user,
                name=user.username,
                registration_number=reg_num,
                address=user.address or "",
                city="",
                state="",
                zip_code="",
                phone=user.phone_number or "",
                email=user.email or ""
            )
            # Handle verification document for hospital
            if 'verification_document' in self.request.FILES:
                hospital.verification_document = self.request.FILES['verification_document']
                hospital.save()
        
        messages.success(
            self.request,
            f'Registration successful! {"Your account is pending approval." if user.role in ["DOCTOR", "HOSPITAL"] else "You can now login."}'
        )
        return redirect(self.success_url)


def login_view(request):
    """Custom login view"""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard_redirect')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()
            password = form.cleaned_data['password']
            try:
                user_obj = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                user_obj = None

            # Check password manually so we can show the right message for blocked/pending users
            # (authenticate() returns None for inactive users, so we'd only see "Invalid email or password")
            if user_obj is not None and user_obj.check_password(password):
                user = user_obj
                # Account exists and password is correct — now check status
                if not user.is_active:
                    messages.error(
                        request,
                        'Your account has been blocked. You cannot sign in. Please contact the administrator for assistance.'
                    )
                    return render(request, 'accounts/login.html', {'form': form})
                if user.role == 'DOCTOR' and not user.is_approved:
                    messages.warning(
                        request,
                        'Your doctor account is pending approval. You will be able to sign in after an administrator approves your account. Please wait or contact support.'
                    )
                    return render(request, 'accounts/login.html', {'form': form})
                if user.role == 'HOSPITAL' and not user.is_approved:
                    messages.warning(
                        request,
                        'Your hospital account is pending approval. You will be able to sign in after an administrator approves your account. Please wait or contact support.'
                    )
                    return render(request, 'accounts/login.html', {'form': form})
                # All checks passed — log the user in
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                return redirect('accounts:dashboard_redirect')

            # Wrong password or no user with this email
            messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


class CustomLogoutView(LogoutView):
    """Custom logout view"""
    next_page = 'accounts:login'
    
    def dispatch(self, request, *args, **kwargs):
        messages.success(request, 'You have been logged out successfully.')
        return super().dispatch(request, *args, **kwargs)


def dashboard_redirect(request):
    """Redirect users to their role-specific dashboard"""
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    # Check if user account is blocked
    if not request.user.is_active:
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, 'Your account has been blocked. Please contact the administrator.')
        return redirect('accounts:login')
    
    role = request.user.role
    
    if role == 'ADMIN':
        return redirect('accounts:admin_dashboard')
    elif role == 'DOCTOR':
        return redirect('accounts:doctor_dashboard')
    elif role == 'PATIENT':
        return redirect('accounts:patient_dashboard')
    elif role == 'HOSPITAL':
        return redirect('accounts:hospital_dashboard')
    else:
        messages.error(request, 'Invalid user role.')
        return redirect('accounts:login')


class AdminDashboardView(AdminRequiredMixin, TemplateView):
    """Admin dashboard view"""
    template_name = 'accounts/admin_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics
        context['total_users'] = User.objects.count()
        context['total_patients'] = User.objects.filter(role='PATIENT').count()
        context['total_doctors'] = User.objects.filter(role='DOCTOR').count()
        context['total_hospitals'] = User.objects.filter(role='HOSPITAL').count()
        context['total_appointments'] = Appointment.objects.count()
        
        # Pending approvals with profile information
        pending_doctors_list = []
        for doctor_user in User.objects.filter(role='DOCTOR', is_approved=False).select_related('doctor_profile'):
            doctor_profile = getattr(doctor_user, 'doctor_profile', None)
            pending_doctors_list.append({
                'user': doctor_user,
                'profile': doctor_profile,
                'has_verification': doctor_profile.verification_document if doctor_profile else False
            })
        context['pending_doctors'] = pending_doctors_list
        
        pending_hospitals_list = []
        for hospital_user in User.objects.filter(role='HOSPITAL', is_approved=False).select_related('hospital_profile'):
            hospital = getattr(hospital_user, 'hospital_profile', None)
            pending_hospitals_list.append({
                'user': hospital_user,
                'hospital': hospital,
                'has_verification': hospital.verification_document if hospital else False
            })
        context['pending_hospitals'] = pending_hospitals_list
        
        return context


class DoctorDashboardView(DoctorRequiredMixin, TemplateView):
    """Doctor dashboard view"""
    template_name = 'accounts/doctor_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        doctor_profile = getattr(self.request.user, 'doctor_profile', None)
        
        # Statistics
        context['total_appointments'] = Appointment.objects.filter(doctor=self.request.user).count()
        context['today_appointments'] = Appointment.objects.filter(
            doctor=self.request.user,
            appointment_date=timezone.now().date()
        ).count()
        context['pending_appointments'] = Appointment.objects.filter(
            doctor=self.request.user,
            status='PENDING'
        ).count()
        context['upcoming_appointments'] = Appointment.objects.filter(
            doctor=self.request.user,
            appointment_date__gte=timezone.now().date(),
            status__in=['PENDING', 'CONFIRMED']
        ).order_by('appointment_date', 'appointment_time')[:10]
        
        context['doctor_profile'] = doctor_profile
        
        return context


class PatientDashboardView(PatientRequiredMixin, TemplateView):
    """Patient dashboard view"""
    template_name = 'accounts/patient_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        patient_profile = getattr(self.request.user, 'patient_profile', None)
        
        # Statistics
        context['total_appointments'] = Appointment.objects.filter(patient=self.request.user).count()
        context['upcoming_appointments'] = Appointment.objects.filter(
            patient=self.request.user,
            appointment_date__gte=timezone.now().date(),
            status__in=['PENDING', 'CONFIRMED']
        ).order_by('appointment_date', 'appointment_time')[:10]
        context['total_documents'] = Document.objects.filter(patient=self.request.user).count()
        
        context['patient_profile'] = patient_profile
        
        return context


class HospitalDashboardView(HospitalRequiredMixin, TemplateView):
    """Hospital dashboard view"""
    template_name = 'accounts/hospital_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        hospital = getattr(self.request.user, 'hospital_profile', None)
        
        # Statistics
        if hospital:
            context['total_doctors'] = hospital.doctors.count()
            context['total_appointments'] = Appointment.objects.filter(hospital=hospital).count()
            context['today_appointments'] = Appointment.objects.filter(
                hospital=hospital,
                appointment_date=timezone.now().date()
            ).count()
            context['upcoming_appointments'] = Appointment.objects.filter(
                hospital=hospital,
                appointment_date__gte=timezone.now().date(),
                status__in=['PENDING', 'CONFIRMED']
            ).order_by('appointment_date', 'appointment_time')[:10]
        
        context['hospital'] = hospital
        
        return context


# Admin list and profile views
class AdminUserListView(AdminRequiredMixin, ListView):
    """Admin: list all users"""
    model = User
    template_name = 'accounts/admin_user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    ordering = ['-created_at']

    def get_queryset(self):
        return User.objects.select_related('doctor_profile', 'patient_profile', 'hospital_profile').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['list_type'] = 'users'
        context['page_title'] = 'All Users'
        return context


class AdminPatientListView(AdminRequiredMixin, ListView):
    """Admin: list all patients"""
    model = User
    template_name = 'accounts/admin_user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        return User.objects.filter(role='PATIENT').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['list_type'] = 'patients'
        context['page_title'] = 'All Patients'
        return context


class AdminDoctorListView(AdminRequiredMixin, ListView):
    """Admin: list all doctors"""
    model = User
    template_name = 'accounts/admin_user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        return User.objects.filter(role='DOCTOR').select_related('doctor_profile').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['list_type'] = 'doctors'
        context['page_title'] = 'All Doctors'
        return context


class AdminHospitalListView(AdminRequiredMixin, ListView):
    """Admin: list all hospitals"""
    model = User
    template_name = 'accounts/admin_user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        return User.objects.filter(role='HOSPITAL').select_related('hospital_profile').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['list_type'] = 'hospitals'
        context['page_title'] = 'All Hospitals'
        return context


class AdminUserProfileView(AdminRequiredMixin, DetailView):
    """Admin: view a single user's profile"""
    model = User
    template_name = 'accounts/admin_user_profile.html'
    context_object_name = 'profile_user'

    def get_queryset(self):
        return User.objects.select_related('doctor_profile', 'patient_profile', 'hospital_profile').all()


# Approval views for Admin
def approve_doctor(request, user_id):
    """Approve doctor accounts"""
    if not request.user.is_authenticated or not request.user.is_admin():
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id, role='DOCTOR')
            user.is_approved = True
            user.save()
            messages.success(request, f'Doctor {user.get_full_name() or user.username} has been approved.')
        except User.DoesNotExist:
            messages.error(request, 'Doctor not found.')
    
    return redirect('accounts:admin_dashboard')


def approve_hospital(request, user_id):
    """Approve hospital accounts"""
    if not request.user.is_authenticated or not request.user.is_admin():
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id, role='HOSPITAL')
            user.is_approved = True
            user.save()
            messages.success(request, f'Hospital {user.get_full_name() or user.username} has been approved.')
        except User.DoesNotExist:
            messages.error(request, 'Hospital not found.')
    
    return redirect('accounts:admin_dashboard')


def reject_doctor(request, user_id):
    """Reject doctor accounts"""
    if not request.user.is_authenticated or not request.user.is_admin():
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id, role='DOCTOR')
            user.delete()  # Or you can add a rejection_reason field
            messages.success(request, f'Doctor {user.get_full_name() or user.username} has been rejected and removed.')
        except User.DoesNotExist:
            messages.error(request, 'Doctor not found.')
    
    return redirect('accounts:admin_dashboard')


def reject_hospital(request, user_id):
    """Reject hospital accounts"""
    if not request.user.is_authenticated or not request.user.is_admin():
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id, role='HOSPITAL')
            user.delete()  # Or you can add a rejection_reason field
            messages.success(request, f'Hospital {user.get_full_name() or user.username} has been rejected and removed.')
        except User.DoesNotExist:
            messages.error(request, 'Hospital not found.')
    
    return redirect('accounts:admin_dashboard')


def block_user(request, user_id):
    """Block a user account"""
    if not request.user.is_authenticated or not request.user.is_admin():
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            # Prevent blocking admin accounts
            if user.is_admin():
                messages.error(request, 'Cannot block admin accounts.')
            else:
                user.is_active = False
                user.save()
                messages.success(request, f'User {user.get_full_name() or user.username} has been blocked.')
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
    
    # Redirect back to the referring page or profile page
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('accounts:admin_user_profile', pk=user_id)


def unblock_user(request, user_id):
    """Unblock a user account"""
    if not request.user.is_authenticated or not request.user.is_admin():
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            user.is_active = True
            user.save()
            messages.success(request, f'User {user.get_full_name() or user.username} has been unblocked.')
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
    
    # Redirect back to the referring page or profile page
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('accounts:admin_user_profile', pk=user_id)
