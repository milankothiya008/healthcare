"""Hospital Admin Dashboard - only HOSPITAL/HOSPITAL_ADMIN role, own hospital data only"""
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView, UpdateView
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator

from accounts.mixins import HospitalRequiredMixin
from .models import Hospital, DoctorHospitalRequest, DoctorHospitalAssignment, Admission
from doctors.models import DoctorProfile
from appointments.models import Appointment


def get_hospital(request):
    """Ensure hospital admin only accesses their own hospital"""
    if not request.user.is_authenticated:
        return None
    if request.user.role not in ('HOSPITAL', 'HOSPITAL_ADMIN'):
        return None
    return getattr(request.user, 'hospital_profile', None)


class HospitalAdminDashboardView(HospitalRequiredMixin, TemplateView):
    """Hospital Admin Dashboard - summary stats"""
    template_name = 'hospitals/admin/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hospital = get_hospital(self.request)
        if not hospital:
            return context

        today = timezone.now().date()
        context['hospital'] = hospital
        context['total_doctors'] = hospital.get_doctors().count()
        context['total_appointments'] = Appointment.objects.filter(hospital=hospital).count()
        context['today_appointments'] = Appointment.objects.filter(
            hospital=hospital,
            appointment_date=today,
            status__in=['PENDING', 'CONFIRMED']
        ).count()
        context['total_admitted'] = hospital.admissions.filter(
            Q(discharge_time__isnull=True) | Q(discharge_time__gt=timezone.now())
        ).count()
        context['available_beds'] = hospital.available_beds_count
        context['occupied_beds'] = hospital.occupied_beds_count
        context['upcoming_appointments'] = Appointment.objects.filter(
            hospital=hospital,
            appointment_date__gte=today,
            status__in=['PENDING', 'CONFIRMED']
        ).order_by('appointment_date', 'appointment_time')[:5]
        return context


class HospitalProfileEditView(HospitalRequiredMixin, UpdateView):
    """Edit hospital profile - includes departments (facilities), contact, website, and admin contact"""
    model = Hospital
    template_name = 'hospitals/admin/profile_edit.html'
    fields = ['name', 'description', 'facilities', 'address', 'city', 'state', 'zip_code', 'phone', 'email', 'website', 'total_beds', 'logo']

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields:
            form.fields[field].widget.attrs.setdefault('class', 'form-control')
        if 'facilities' in form.fields:
            form.fields['facilities'].label = 'Departments (comma-separated)'
            form.fields['facilities'].help_text = 'e.g. Emergency, Cardiology, General Medicine'
        return form

    def get_object(self, queryset=None):
        return get_hospital(self.request)

    def get_success_url(self):
        messages.success(self.request, 'Hospital profile updated successfully.')
        return reverse_lazy('hospitals:admin_profile')

    def get(self, request, *args, **kwargs):
        if not get_hospital(request):
            messages.error(request, 'Hospital profile not found.')
            return redirect('accounts:dashboard_redirect')
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        result = super().form_valid(form)
        # Save admin contact number to user (shown to patients as "Admin contact")
        admin_phone = self.request.POST.get('admin_phone', '').strip()
        if self.request.user.phone_number != admin_phone:
            self.request.user.phone_number = admin_phone
            self.request.user.save(update_fields=['phone_number', 'updated_at'])
        return result


class DoctorRequestListView(HospitalRequiredMixin, ListView):
    """Pending doctor join requests"""
    template_name = 'hospitals/admin/doctor_requests.html'
    context_object_name = 'requests'
    paginate_by = 10

    def get_queryset(self):
        hospital = get_hospital(self.request)
        if not hospital:
            return DoctorHospitalRequest.objects.none()
        return DoctorHospitalRequest.objects.filter(
            hospital=hospital,
            status='PENDING'
        ).select_related('doctor__user').order_by('-created_at')


class DoctorRequestDetailView(HospitalRequiredMixin, DetailView):
    """View full doctor details for a join request"""
    model = DoctorHospitalRequest
    template_name = 'hospitals/admin/doctor_request_detail.html'
    context_object_name = 'request_obj'

    def get_queryset(self):
        hospital = get_hospital(self.request)
        if not hospital:
            return DoctorHospitalRequest.objects.none()
        return DoctorHospitalRequest.objects.filter(hospital=hospital).select_related('doctor__user', 'doctor__hospital')


def approve_doctor_request(request, pk):
    """Approve doctor join request; create assignment with expected salary as final salary"""
    hospital = get_hospital(request)
    if not hospital:
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')

    req = get_object_or_404(DoctorHospitalRequest, pk=pk, hospital=hospital, status='PENDING')
    if request.method == 'POST':
        with transaction.atomic():
            salary = req.expected_monthly_salary or 0
            DoctorHospitalAssignment.objects.get_or_create(
                doctor=req.doctor,
                hospital=hospital,
                defaults={'monthly_salary': salary, 'is_active': True}
            )
            if not req.doctor.hospital_id:
                req.doctor.hospital = hospital
                req.doctor.save(update_fields=['hospital'])
            req.status = 'APPROVED'
            req.save()
        messages.success(request, f'Dr. {req.doctor.user.get_full_name() or req.doctor.user.username} has been approved.')
    return redirect('hospitals:admin_doctor_requests')


def reject_doctor_request(request, pk):
    """Reject doctor join request"""
    hospital = get_hospital(request)
    if not hospital:
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')

    req = get_object_or_404(DoctorHospitalRequest, pk=pk, hospital=hospital, status='PENDING')
    if request.method == 'POST':
        req.status = 'REJECTED'
        req.save()
        messages.success(request, 'Doctor request rejected.')
    return redirect('hospitals:admin_doctor_requests')


class HospitalDoctorListView(HospitalRequiredMixin, ListView):
    """List doctors associated with hospital (assignments + legacy)"""
    template_name = 'hospitals/admin/doctor_list.html'
    context_object_name = 'doctors'
    paginate_by = 15

    def get_queryset(self):
        hospital = get_hospital(self.request)
        if not hospital:
            return DoctorProfile.objects.none()
        return hospital.get_doctors().select_related('user').order_by('user__first_name')


class HospitalDoctorDetailView(HospitalRequiredMixin, DetailView):
    """Doctor detail - with remove option"""
    model = DoctorProfile
    template_name = 'hospitals/admin/doctor_detail.html'
    context_object_name = 'doctor'

    def get_queryset(self):
        hospital = get_hospital(self.request)
        if not hospital:
            return DoctorProfile.objects.none()
        return hospital.get_doctors().select_related('user')


def remove_doctor(request, pk):
    """Remove doctor from hospital - deactivate assignment or clear legacy FK; only if no pending/upcoming appointments"""
    hospital = get_hospital(request)
    if not hospital:
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')

    doctor = get_object_or_404(DoctorProfile, pk=pk)
    if doctor not in hospital.get_doctors():
        messages.error(request, 'Doctor is not associated with this hospital.')
        return redirect('hospitals:admin_doctor_list')

    today = timezone.now().date()
    pending = Appointment.objects.filter(
        doctor=doctor.user,
        hospital=hospital,
        status__in=['PENDING', 'CONFIRMED'],
        appointment_date__gte=today
    ).exists()

    if pending:
        messages.error(request, 'Cannot remove doctor. There are pending or upcoming appointments.')
        return redirect('hospitals:admin_doctor_detail', pk=pk)

    if request.method == 'POST':
        with transaction.atomic():
            assignment = DoctorHospitalAssignment.objects.filter(doctor=doctor, hospital=hospital, is_active=True).first()
            if assignment:
                assignment.is_active = False
                assignment.save()
            if doctor.hospital_id == hospital.id:
                doctor.hospital = None
                doctor.save(update_fields=['hospital'])
        messages.success(request, 'Doctor removed from hospital.')
        return redirect('hospitals:admin_doctor_list')
    return redirect('hospitals:admin_doctor_detail', pk=pk)


class HospitalAppointmentListView(HospitalRequiredMixin, ListView):
    """Manage appointments - filter by status"""
    template_name = 'hospitals/admin/appointment_list.html'
    context_object_name = 'appointments'
    paginate_by = 15

    def get_queryset(self):
        hospital = get_hospital(self.request)
        if not hospital:
            return Appointment.objects.none()

        qs = Appointment.objects.filter(hospital=hospital).select_related('patient', 'doctor').order_by('-appointment_date', '-appointment_time')
        status = self.request.GET.get('status', '')
        today = timezone.now().date()

        if status == 'today':
            qs = qs.filter(appointment_date=today)
        elif status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_status'] = self.request.GET.get('status', '')
        context['status_choices'] = Appointment.STATUS_CHOICES
        context['status_transitions'] = APPOINTMENT_STATUS_TRANSITIONS
        return context


# Allowed status transitions: from_status -> [to_statuses]
APPOINTMENT_STATUS_TRANSITIONS = {
    'PENDING': ['CONFIRMED', 'CANCELLED'],
    'CONFIRMED': ['COMPLETED', 'CANCELLED'],
    'COMPLETED': [],   # read-only
    'CANCELLED': [],   # read-only
    'RESCHEDULED': ['CONFIRMED', 'CANCELLED'],
}


def update_appointment_status(request, pk):
    """Update appointment status - only valid transitions allowed. Completed/Cancelled are read-only."""
    hospital = get_hospital(request)
    if not hospital:
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')

    apt = get_object_or_404(Appointment, pk=pk, hospital=hospital)
    if request.method == 'POST':
        new_status = request.POST.get('status', '').strip()
        allowed = APPOINTMENT_STATUS_TRANSITIONS.get(apt.status, [])
        if new_status in dict(Appointment.STATUS_CHOICES) and new_status in allowed:
            apt.status = new_status
            apt.save(update_fields=['status', 'updated_at'])
            messages.success(request, f'Appointment status updated to {dict(Appointment.STATUS_CHOICES).get(new_status, new_status)}.')
        else:
            messages.error(request, 'Invalid status transition or status is read-only.')
    return redirect('hospitals:admin_appointments')


class AdmissionListView(HospitalRequiredMixin, ListView):
    """Admission history"""
    template_name = 'hospitals/admin/admission_list.html'
    context_object_name = 'admissions'
    paginate_by = 15

    def get_queryset(self):
        hospital = get_hospital(self.request)
        if not hospital:
            return Admission.objects.none()
        return Admission.objects.filter(hospital=hospital).select_related('patient', 'doctor').order_by('-admission_time')


def admit_patient(request):
    """Create admission - for emergency when patient is admitted"""
    hospital = get_hospital(request)
    if not hospital:
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')

    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        doctor_id = request.POST.get('doctor_id')
        appointment_id = request.POST.get('appointment_id')
        expected_discharge = request.POST.get('expected_discharge_time', '').strip()

        from accounts.models import User
        patient = get_object_or_404(User, pk=patient_id, role='PATIENT')
        doctor = get_object_or_404(User, pk=doctor_id, role='DOCTOR') if doctor_id else None
        appointment = get_object_or_404(Appointment, pk=appointment_id, hospital=hospital) if appointment_id else None

        if hospital.available_beds_count <= 0:
            messages.error(request, 'No beds available.')
            return redirect('hospitals:admin_dashboard')

        try:
            expected_dt = datetime.strptime(expected_discharge, '%Y-%m-%dT%H:%M') if expected_discharge else None
            if expected_dt and expected_dt <= timezone.now():
                messages.error(request, 'Expected discharge must be in the future.')
                return redirect('hospitals:admin_admissions')
        except ValueError:
            expected_dt = None

        Admission.objects.create(
            patient=patient,
            hospital=hospital,
            doctor=doctor,
            appointment=appointment,
            admission_time=timezone.now(),
            expected_discharge_time=expected_dt
        )
        messages.success(request, 'Patient admitted successfully.')
    return redirect('hospitals:admin_admissions')


def discharge_patient(request, pk):
    """Set discharge_time - bed becomes available"""
    hospital = get_hospital(request)
    if not hospital:
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')

    admission = get_object_or_404(Admission, pk=pk, hospital=hospital)
    if request.method == 'POST':
        discharge_str = request.POST.get('discharge_time', '').strip()
        if not discharge_str:
            messages.error(request, 'Discharge time is required.')
            return redirect('hospitals:admin_admissions')

        try:
            discharge_dt = datetime.strptime(discharge_str, '%Y-%m-%dT%H:%M')
            if timezone.is_naive(discharge_dt):
                discharge_dt = timezone.make_aware(discharge_dt, timezone.get_current_timezone())
            if discharge_dt < admission.admission_time:
                messages.error(request, 'Discharge time cannot be earlier than admission time.')
                return redirect('hospitals:admin_admissions')
            admission.discharge_time = discharge_dt
            admission.save()
            messages.success(request, 'Patient discharged successfully.')
        except (ValueError, TypeError):
            messages.error(request, 'Invalid date/time format.')
    return redirect('hospitals:admin_admissions')
