from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LogoutView
from django.contrib import messages
from django.views import View
from django.views.generic import CreateView, TemplateView, ListView, DetailView
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import uuid

from .forms import UserRegistrationForm, LoginForm, DoctorProfileEditForm
from .mixins import (
    AdminRequiredMixin, DoctorRequiredMixin, 
    PatientRequiredMixin, HospitalRequiredMixin
)
from .models import User
from patients.models import PatientProfile
from doctors.models import DoctorProfile, DoctorProfileUpdateRequest
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
    elif role in ('HOSPITAL', 'HOSPITAL_ADMIN'):
        return redirect('hospitals:admin_dashboard')
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
        context['pending_profile_requests_count'] = DoctorProfileUpdateRequest.objects.filter(status='PENDING').count()

        return context


class DoctorDashboardView(DoctorRequiredMixin, TemplateView):
    """Doctor dashboard view - dynamic summary; only own data"""
    template_name = 'accounts/doctor_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        doctor_profile = getattr(user, 'doctor_profile', None)
        today = timezone.now().date()

        base_qs = Appointment.objects.filter(doctor=user)
        context['today_appointments'] = base_qs.filter(appointment_date=today).count()
        context['today_appointments_list'] = base_qs.filter(
            appointment_date=today,
            status__in=['PENDING', 'CONFIRMED']
        ).select_related('patient', 'hospital').order_by('appointment_time')
        context['upcoming_appointments'] = base_qs.filter(
            appointment_date__gte=today,
            status__in=['PENDING', 'CONFIRMED']
        ).select_related('patient', 'hospital').order_by('appointment_date', 'appointment_time')[:10]
        context['total_completed_appointments'] = base_qs.filter(status='COMPLETED').count()
        context['pending_requests'] = base_qs.filter(status='PENDING').count()
        context['doctor_profile'] = doctor_profile
        context['pending_profile_requests'] = DoctorProfileUpdateRequest.objects.filter(
            doctor=doctor_profile, status='PENDING'
        ).count() if doctor_profile else 0
        return context


class DoctorProfileEditView(DoctorRequiredMixin, TemplateView):
    """Doctor profile edit: non-sensitive saves immediately; sensitive creates update request"""
    template_name = 'accounts/doctor_profile_edit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor_profile = getattr(self.request.user, 'doctor_profile', None)
        context['doctor_profile'] = doctor_profile
        context['form'] = DoctorProfileEditForm(user=self.request.user, doctor_profile=doctor_profile)
        context['pending_requests'] = list(
            DoctorProfileUpdateRequest.objects.filter(doctor=doctor_profile, status='PENDING').order_by('-created_at')
        ) if doctor_profile else []
        return context

    def post(self, request, *args, **kwargs):
        doctor_profile = getattr(request.user, 'doctor_profile', None)
        if not doctor_profile:
            messages.error(request, 'Doctor profile not found.')
            return redirect('accounts:doctor_dashboard')
        form = DoctorProfileEditForm(
            request.POST, request.FILES,
            user=request.user, doctor_profile=doctor_profile
        )
        if not form.is_valid():
            context = self.get_context_data()
            context['form'] = form
            context['pending_requests'] = list(
                DoctorProfileUpdateRequest.objects.filter(doctor=doctor_profile, status='PENDING').order_by('-created_at')
            )
            return render(request, self.template_name, context)
        form.save_non_sensitive()
        form.create_update_requests()
        messages.success(
            request,
            'Profile updated. Non-sensitive changes are saved. Sensitive changes are pending admin approval.'
        )
        return redirect('accounts:doctor_profile_edit')


class DoctorProfilePhotoUploadView(DoctorRequiredMixin, View):
    """Upload profile photo (click on photo); updates immediately"""

    def post(self, request):
        doctor_profile = getattr(request.user, 'doctor_profile', None)
        if not doctor_profile:
            messages.error(request, 'Profile not found.')
            return redirect('accounts:doctor_dashboard')
        photo = request.FILES.get('profile_picture')
        if not photo:
            messages.error(request, 'No image provided.')
            return redirect('accounts:doctor_profile_edit')
        request.user.profile_picture = photo
        request.user.save(update_fields=['profile_picture', 'updated_at'])
        doctor_profile.profile_picture = photo
        doctor_profile.save(update_fields=['profile_picture', 'updated_at'])
        messages.success(request, 'Profile photo updated.')
        return redirect('accounts:doctor_profile_edit')


class PatientDashboardView(PatientRequiredMixin, TemplateView):
    """Patient dashboard view"""
    template_name = 'accounts/patient_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        patient_profile = getattr(self.request.user, 'patient_profile', None)
        
        # Statistics
        all_appointments = Appointment.objects.filter(patient=self.request.user)
        context['total_appointments'] = all_appointments.count()
        context['past_appointments_count'] = all_appointments.filter(
            Q(appointment_date__lt=today) | Q(status='COMPLETED')
        ).count()
        context['upcoming_appointments'] = all_appointments.filter(
            appointment_date__gte=today,
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
            context['total_doctors'] = hospital.get_doctors().count()
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


class AdminDoctorProfileUpdateRequestListView(AdminRequiredMixin, ListView):
    """System Admin: list doctor profile update requests (sensitive fields)"""
    template_name = 'accounts/admin_doctor_profile_requests.html'
    context_object_name = 'requests'
    paginate_by = 20

    def get_queryset(self):
        return DoctorProfileUpdateRequest.objects.filter(status='PENDING').select_related('doctor__user').order_by('-created_at')


def admin_approve_doctor_profile_request(request, pk):
    """Apply sensitive change to doctor profile and mark request approved"""
    if not request.user.is_authenticated or not request.user.is_admin():
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')
    req = get_object_or_404(DoctorProfileUpdateRequest, pk=pk, status='PENDING')
    if request.method == 'POST':
        from django.utils import timezone as tz
        profile = req.doctor
        if req.field_name == 'specialization':
            profile.specialization = req.new_value_text
            profile.save(update_fields=['specialization', 'updated_at'])
        elif req.field_name == 'qualification':
            profile.qualification = req.new_value_text
            profile.save(update_fields=['qualification', 'updated_at'])
        elif req.field_name == 'license_number':
            profile.license_number = req.new_value_text
            profile.save(update_fields=['license_number', 'updated_at'])
        elif req.field_name == 'verification_document' and req.new_value_file:
            profile.verification_document = req.new_value_file
            profile.save(update_fields=['verification_document', 'updated_at'])
        req.status = 'APPROVED'
        req.reviewed_at = tz.now()
        req.reviewed_by = request.user
        req.save(update_fields=['status', 'reviewed_at', 'reviewed_by'])
        messages.success(request, 'Doctor profile update approved and applied.')
    return redirect('accounts:admin_doctor_profile_requests')


def admin_reject_doctor_profile_request(request, pk):
    """Reject request; no change to profile"""
    if not request.user.is_authenticated or not request.user.is_admin():
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')
    req = get_object_or_404(DoctorProfileUpdateRequest, pk=pk, status='PENDING')
    if request.method == 'POST':
        from django.utils import timezone as tz
        req.status = 'REJECTED'
        req.reviewed_at = tz.now()
        req.reviewed_by = request.user
        req.save(update_fields=['status', 'reviewed_at', 'reviewed_by'])
        messages.success(request, 'Doctor profile update rejected.')
    return redirect('accounts:admin_doctor_profile_requests')


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
