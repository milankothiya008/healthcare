from datetime import time, timedelta, datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, TemplateView, FormView
from django.views import View
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.urls import reverse_lazy

from accounts.mixins import DoctorRequiredMixin
from .models import DoctorProfile, DoctorLeave
from appointments.models import Appointment
from hospitals.models import Hospital, DoctorHospitalRequest, DoctorHospitalAssignment


class DoctorSearchView(LoginRequiredMixin, ListView):
    """Search doctors - only approved doctors with hospital association"""
    model = DoctorProfile
    template_name = 'doctors/doctor_search.html'
    context_object_name = 'doctors'
    paginate_by = 10

    def get_queryset(self):
        # Only approved doctors assigned to at least one hospital (legacy FK or assignment)
        qs = DoctorProfile.objects.select_related('user', 'hospital').filter(
            user__is_approved=True,
            user__is_active=True
        ).filter(
            Q(hospital__isnull=False) | Q(hospital_assignments__is_active=True)
        ).distinct()
        q = self.request.GET.get('q', '').strip()
        specialization = self.request.GET.get('specialization', '').strip()
        hospital_name = self.request.GET.get('hospital', '').strip()

        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(user__username__icontains=q)
            )
        if specialization:
            qs = qs.filter(specialization=specialization)
        if hospital_name:
            qs = qs.filter(
                Q(hospital__name__icontains=hospital_name) |
                Q(hospital_assignments__hospital__name__icontains=hospital_name)
            ).distinct()

        return qs.order_by('user__first_name', 'user__last_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_q'] = self.request.GET.get('q', '')
        context['search_specialization'] = self.request.GET.get('specialization', '')
        context['search_hospital'] = self.request.GET.get('hospital', '')
        context['specialization_choices'] = DoctorProfile.SPECIALIZATION_CHOICES
        return context


class DoctorDetailView(LoginRequiredMixin, DetailView):
    """Doctor detail with available dates and time slots"""
    model = DoctorProfile
    template_name = 'doctors/doctor_detail.html'
    context_object_name = 'doctor'

    def get_queryset(self):
        return DoctorProfile.objects.select_related('user', 'hospital').filter(
            user__is_approved=True,
            user__is_active=True
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = self.object
        today = timezone.now().date()
        leave_dates = set(DoctorLeave.objects.filter(doctor=doctor).values_list('leave_date', flat=True))

        # Hospitals where doctor works (legacy + assignments)
        doctor_hospitals = []
        if doctor.hospital_id:
            doctor_hospitals.append(doctor.hospital)
        for a in DoctorHospitalAssignment.objects.filter(doctor=doctor, is_active=True).select_related('hospital'):
            if a.hospital not in doctor_hospitals:
                doctor_hospitals.append(a.hospital)
        context['doctor_hospitals'] = doctor_hospitals

        # Generate next 14 days as available dates (exclude leave)
        available_dates = []
        for i in range(14):
            d = today + timedelta(days=i)
            if d not in leave_dates:
                available_dates.append(d)
        context['available_dates'] = available_dates

        # Get selected date from request
        context['available_slots'] = []
        selected_date_str = self.request.GET.get('date', '')
        if selected_date_str:
            try:
                selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
                if selected_date >= today:
                    context['selected_date'] = selected_date
                    context['available_slots'] = self._get_available_slots(doctor, selected_date)
            except (ValueError, TypeError):
                pass

        return context

    def _get_available_slots(self, doctor, appointment_date):
        """Generate time slots within doctor's schedule. Booked slots are GLOBAL (any hospital):
        if the doctor has 10 AM booked at Hospital A, 10 AM is unavailable at Hospital B too."""
        today = timezone.now().date()
        now_time = timezone.now().time()

        # Global conflict: exclude any slot already booked for this doctor on this date (any hospital)
        booked = set(
            Appointment.objects.filter(
                doctor=doctor.user,
                appointment_date=appointment_date,
                status__in=['PENDING', 'CONFIRMED']
            ).values_list('appointment_time', flat=True)
        )

        slots = []
        current = doctor.available_from
        end = doctor.available_to
        delta = timedelta(minutes=doctor.slot_duration_minutes)

        while current < end:
            # Skip past times if today
            if appointment_date == today and current <= now_time:
                dt = datetime.combine(appointment_date, current) + delta
                current = dt.time()
                continue

            if current not in booked:
                slots.append(current)

            # Advance by slot duration
            dt = datetime.combine(appointment_date, current) + delta
            current = dt.time()

        return slots


def request_join_hospital(request, hospital_id):
    """Doctor sends work request to hospital with expected monthly salary (POST only with expected_monthly_salary)"""
    if not request.user.is_authenticated or request.user.role != 'DOCTOR':
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')
    if not request.user.is_approved:
        messages.error(request, 'Your account must be approved by the system admin first.')
        return redirect('accounts:doctor_dashboard')

    hospital = get_object_or_404(Hospital, pk=hospital_id)
    doctor_profile = getattr(request.user, 'doctor_profile', None)
    if not doctor_profile:
        messages.error(request, 'Doctor profile not found.')
        return redirect('accounts:doctor_dashboard')

    if request.method != 'POST':
        return redirect('doctors:doctor_hospital_list')

    try:
        salary = Decimal(request.POST.get('expected_monthly_salary', 0) or 0)
    except Exception:
        salary = Decimal('0')
    if salary < 0:
        messages.error(request, 'Please enter a valid expected monthly salary.')
        return redirect('doctors:doctor_send_request', hospital_id=hospital_id)

    req, created = DoctorHospitalRequest.objects.get_or_create(
        doctor=doctor_profile,
        hospital=hospital,
        defaults={'status': 'PENDING', 'expected_monthly_salary': salary}
    )
    if not created:
        if req.status == 'PENDING':
            messages.info(request, 'You already have a pending request for this hospital.')
        elif req.status == 'APPROVED':
            messages.info(request, 'You are already associated with this hospital.')
        else:
            req.status = 'PENDING'
            req.expected_monthly_salary = salary
            req.save()
            messages.success(request, 'Join request sent with expected salary.')
    else:
        req.expected_monthly_salary = salary
        req.save()
        messages.success(request, f'Join request sent to {hospital.name}.')
    return redirect('doctors:doctor_hospital_list')


# ----- Doctor dashboard: hospitals, availability, appointments -----

class DoctorHospitalListView(DoctorRequiredMixin, ListView):
    """List all hospitals; doctor can send work request with expected salary"""
    template_name = 'doctors/doctor_hospital_list.html'
    context_object_name = 'hospitals'
    model = Hospital
    paginate_by = 15

    def get_queryset(self):
        return Hospital.objects.all().order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor_profile = getattr(self.request.user, 'doctor_profile', None)
        my_requests = {}
        my_assignments = set()
        if doctor_profile:
            my_requests = {
                r.hospital_id: r for r in DoctorHospitalRequest.objects.filter(doctor=doctor_profile).select_related('hospital')
            }
            my_assignments = set(
                DoctorHospitalAssignment.objects.filter(doctor=doctor_profile, is_active=True).values_list('hospital_id', flat=True)
            )
        # Build list with status per hospital for template (current page)
        context['hospital_list'] = []
        for hospital in context.get('object_list', []):
            context['hospital_list'].append({
                'hospital': hospital,
                'request_obj': my_requests.get(hospital.id),
                'is_assigned': hospital.id in my_assignments,
            })
        return context


class DoctorSendRequestView(DoctorRequiredMixin, TemplateView):
    """Show form to send work request with expected monthly salary"""
    template_name = 'doctors/doctor_send_request.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hospital'] = get_object_or_404(Hospital, pk=self.kwargs['hospital_id'])
        return context


class DoctorAvailabilityView(DoctorRequiredMixin, TemplateView):
    """Edit working hours, slot duration, and leave dates"""
    template_name = 'doctors/doctor_availability.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor_profile = getattr(self.request.user, 'doctor_profile', None)
        context['doctor_profile'] = doctor_profile
        if doctor_profile:
            context['leave_dates'] = list(DoctorLeave.objects.filter(doctor=doctor_profile).order_by('leave_date').values_list('leave_date', flat=True))
            context['available_from_str'] = doctor_profile.available_from.strftime('%H:%M')
            context['available_to_str'] = doctor_profile.available_to.strftime('%H:%M')
        else:
            context['leave_dates'] = []
        return context

    def post(self, request, *args, **kwargs):
        doctor_profile = getattr(request.user, 'doctor_profile', None)
        if not doctor_profile:
            messages.error(request, 'Profile not found.')
            return redirect('accounts:doctor_dashboard')
        action = request.POST.get('action')
        if action == 'save_hours':
            try:
                doctor_profile.available_from = datetime.strptime(request.POST.get('available_from', '09:00'), '%H:%M').time()
                doctor_profile.available_to = datetime.strptime(request.POST.get('available_to', '17:00'), '%H:%M').time()
                doctor_profile.slot_duration_minutes = int(request.POST.get('slot_duration_minutes', 30))
                doctor_profile.save(update_fields=['available_from', 'available_to', 'slot_duration_minutes', 'updated_at'])
                messages.success(request, 'Working hours and slot duration updated.')
            except (ValueError, TypeError):
                messages.error(request, 'Invalid time or slot duration.')
        elif action == 'add_leave':
            leave_str = request.POST.get('leave_date', '')
            try:
                leave_date = datetime.strptime(leave_str, '%Y-%m-%d').date()
                if leave_date < timezone.now().date():
                    messages.error(request, 'Leave date must be today or in the future.')
                else:
                    DoctorLeave.objects.get_or_create(doctor=doctor_profile, leave_date=leave_date)
                    messages.success(request, f'Leave added for {leave_date}.')
            except (ValueError, TypeError):
                messages.error(request, 'Invalid date.')
        elif action == 'remove_leave':
            leave_str = request.POST.get('leave_date', '')
            try:
                leave_date = datetime.strptime(leave_str, '%Y-%m-%d').date()
                DoctorLeave.objects.filter(doctor=doctor_profile, leave_date=leave_date).delete()
                messages.success(request, 'Leave date removed.')
            except (ValueError, TypeError):
                pass
        return redirect('doctors:doctor_availability')


class DoctorAppointmentListView(DoctorRequiredMixin, ListView):
    """Today, upcoming, or full history - only own appointments"""
    template_name = 'doctors/doctor_appointment_list.html'
    context_object_name = 'appointments'
    paginate_by = 15

    def get_queryset(self):
        today = timezone.now().date()
        qs = Appointment.objects.filter(doctor=self.request.user).select_related('patient', 'hospital').order_by('-appointment_date', '-appointment_time')
        f = self.request.GET.get('filter', '')
        if f == 'today':
            qs = qs.filter(appointment_date=today)
        elif f == 'upcoming':
            qs = qs.filter(appointment_date__gte=today, status__in=['PENDING', 'CONFIRMED'])
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.request.GET.get('filter', '')
        return context


class DoctorAppointmentDetailView(DoctorRequiredMixin, DetailView):
    """View patient details, notes, prescription; approve/reject/complete"""
    model = Appointment
    template_name = 'doctors/doctor_appointment_detail.html'
    context_object_name = 'appointment'

    def get_queryset(self):
        return Appointment.objects.filter(doctor=self.request.user).select_related('patient', 'hospital')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        apt = self.object
        today = timezone.now().date()
        now_time = timezone.now().time()
        context['can_approve_reject'] = apt.status == 'PENDING'
        context['can_complete'] = (
            apt.status in ('PENDING', 'CONFIRMED') and
            (apt.appointment_date < today or (apt.appointment_date == today and apt.appointment_time <= now_time))
        )
        context['is_past_completed'] = apt.status == 'COMPLETED'
        return context


def doctor_appointment_approve(request, pk):
    """Approve: PENDING -> CONFIRMED"""
    if not request.user.is_authenticated or request.user.role != 'DOCTOR':
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')
    apt = get_object_or_404(Appointment, pk=pk, doctor=request.user)
    if apt.status != 'PENDING':
        messages.error(request, 'Only pending appointments can be approved.')
        return redirect('doctors:doctor_appointment_detail', pk=pk)
    if request.method == 'POST':
        apt.status = 'CONFIRMED'
        apt.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'Appointment confirmed.')
    return redirect('doctors:doctor_appointment_detail', pk=pk)


def doctor_appointment_reject(request, pk):
    """Reject: PENDING -> CANCELLED"""
    if not request.user.is_authenticated or request.user.role != 'DOCTOR':
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')
    apt = get_object_or_404(Appointment, pk=pk, doctor=request.user)
    if apt.status != 'PENDING':
        messages.error(request, 'Only pending appointments can be rejected.')
        return redirect('doctors:doctor_appointment_detail', pk=pk)
    if request.method == 'POST':
        apt.status = 'CANCELLED'
        apt.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'Appointment cancelled.')
    return redirect('doctors:doctor_appointment_detail', pk=pk)


def doctor_appointment_complete(request, pk):
    """Mark as COMPLETED (only after appointment time); do not allow for past completed"""
    if not request.user.is_authenticated or request.user.role != 'DOCTOR':
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')
    apt = get_object_or_404(Appointment, pk=pk, doctor=request.user)
    if apt.status == 'COMPLETED':
        messages.info(request, 'Appointment is already completed.')
        return redirect('doctors:doctor_appointment_detail', pk=pk)
    if apt.status not in ('PENDING', 'CONFIRMED'):
        messages.error(request, 'Only pending or confirmed appointments can be marked completed.')
        return redirect('doctors:doctor_appointment_detail', pk=pk)
    today = timezone.now().date()
    now_time = timezone.now().time()
    if apt.appointment_date > today or (apt.appointment_date == today and apt.appointment_time > now_time):
        messages.error(request, 'You can only mark an appointment complete after its time has passed.')
        return redirect('doctors:doctor_appointment_detail', pk=pk)
    if request.method == 'POST':
        apt.status = 'COMPLETED'
        apt.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'Appointment marked as completed.')
    return redirect('doctors:doctor_appointment_detail', pk=pk)


def doctor_appointment_notes(request, pk):
    """Update consultation notes and/or prescription"""
    if not request.user.is_authenticated or request.user.role != 'DOCTOR':
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')
    apt = get_object_or_404(Appointment, pk=pk, doctor=request.user)
    if request.method == 'POST':
        apt.notes = request.POST.get('notes', apt.notes)
        apt.prescription = request.POST.get('prescription', apt.prescription)
        apt.save(update_fields=['notes', 'prescription', 'updated_at'])
        messages.success(request, 'Notes and prescription updated.')
    return redirect('doctors:doctor_appointment_detail', pk=pk)
