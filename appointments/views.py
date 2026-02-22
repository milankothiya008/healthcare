from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from .models import Appointment
from doctors.models import DoctorProfile
from hospitals.models import Hospital
from accounts.mixins import PatientRequiredMixin


class AppointmentHistoryView(PatientRequiredMixin, ListView):
    """Patient appointment history - upcoming and past"""
    model = Appointment
    template_name = 'appointments/appointment_history.html'
    context_object_name = 'appointments'
    paginate_by = 15

    def get_queryset(self):
        tab = self.request.GET.get('tab', 'upcoming')
        qs = Appointment.objects.filter(patient=self.request.user).select_related(
            'doctor', 'hospital', 'doctor__doctor_profile'
        ).order_by('-appointment_date', '-appointment_time')

        today = timezone.now().date()
        if tab == 'past':
            qs = qs.filter(appointment_date__lt=today)
        else:
            qs = qs.filter(
                appointment_date__gte=today,
                status__in=['PENDING', 'CONFIRMED']
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tab'] = self.request.GET.get('tab', 'upcoming')
        today = timezone.now().date()
        context['past_count'] = Appointment.objects.filter(
            patient=self.request.user,
            appointment_date__lt=today
        ).count()
        context['upcoming_count'] = Appointment.objects.filter(
            patient=self.request.user,
            appointment_date__gte=today,
            status__in=['PENDING', 'CONFIRMED']
        ).count()
        return context


def book_normal_appointment(request, doctor_id):
    """Book normal appointment - select hospital, date, time slot"""
    if not request.user.is_authenticated or request.user.role != 'PATIENT':
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')

    doctor = get_object_or_404(DoctorProfile, pk=doctor_id, user__is_approved=True, user__is_active=True)
    if not doctor.hospital:
        messages.error(request, 'This doctor is not associated with a hospital.')
        return redirect('doctors:doctor_search')

    today = timezone.now().date()

    if request.method == 'POST':
        hospital_id = request.POST.get('hospital_id')
        date_str = request.POST.get('date')
        time_str = request.POST.get('time')
        reason = request.POST.get('reason', '').strip()

        errors = []
        if not reason:
            errors.append('Reason is required.')

        try:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            if appointment_date < today:
                errors.append('Cannot book in the past.')
        except (ValueError, TypeError):
            errors.append('Invalid date.')

        try:
            appointment_time = datetime.strptime(time_str, '%H:%M').time()
        except (ValueError, TypeError):
            errors.append('Invalid time.')

        hospital = None
        if hospital_id:
            hospital = get_object_or_404(Hospital, pk=hospital_id)
            if doctor.hospital_id != hospital.id:
                errors.append('Invalid hospital selection.')
        else:
            hospital = doctor.hospital

        if errors:
            for e in errors:
                messages.error(request, e)
            return redirect('appointments:book_normal', doctor_id=doctor_id)

        # Check double booking
        if Appointment.objects.filter(
            doctor=doctor.user,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status__in=['PENDING', 'CONFIRMED']
        ).exists():
            messages.error(request, 'This time slot is already booked.')
            return redirect('appointments:book_normal', doctor_id=doctor_id)

        Appointment.objects.create(
            patient=request.user,
            doctor=doctor.user,
            hospital=hospital,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            reason=reason,
            is_emergency=False,
            status='PENDING'
        )
        messages.success(request, 'Appointment booked successfully! Status: Pending.')
        return redirect('appointments:history')

    return redirect('doctors:doctor_detail', pk=doctor_id)


def emergency_hospital_list(request):
    """List hospitals with available beds > 0 for emergency booking"""
    if not request.user.is_authenticated or request.user.role != 'PATIENT':
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')

    # Optional search
    q = request.GET.get('q', '').strip()
    city = request.GET.get('city', '').strip()
    hospitals_qs = Hospital.objects.select_related('user').order_by('name')
    if q:
        hospitals_qs = hospitals_qs.filter(
            Q(name__icontains=q) | Q(address__icontains=q) | Q(city__icontains=q)
        )
    if city:
        hospitals_qs = hospitals_qs.filter(city__icontains=city)
    # Filter to only hospitals with available beds (computed dynamically)
    hospitals = [h for h in hospitals_qs if h.available_beds_count > 0]

    from django.core.paginator import Paginator
    paginator = Paginator(hospitals, 10)
    page = request.GET.get('page', 1)
    hospitals = paginator.get_page(page)

    return render(request, 'appointments/emergency_booking.html', {
        'hospitals': hospitals,
        'search_q': request.GET.get('q', ''),
        'search_city': request.GET.get('city', ''),
    })


def confirm_emergency_booking(request):
    """Confirm emergency booking - create Admission for bed occupancy"""
    if not request.user.is_authenticated or request.user.role != 'PATIENT':
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')

    if request.method != 'POST':
        return redirect('appointments:emergency_booking')

    hospital_id = request.POST.get('hospital_id')
    reason = request.POST.get('reason', 'Emergency').strip() or 'Emergency'

    hospital = get_object_or_404(Hospital, pk=hospital_id)
    if hospital.available_beds_count <= 0:
        messages.error(request, 'No beds available at this hospital.')
        return redirect('appointments:emergency_booking')

    # Get first available doctor at this hospital for emergency
    doctor_profile = hospital.doctors.filter(user__is_approved=True, user__is_active=True).first()
    if not doctor_profile:
        messages.error(request, 'No doctors available at this hospital for emergency.')
        return redirect('appointments:emergency_booking')

    with transaction.atomic():
        from hospitals.models import Admission
        now = timezone.now()
        apt = Appointment.objects.create(
            patient=request.user,
            doctor=doctor_profile.user,
            hospital=hospital,
            appointment_date=now.date(),
            appointment_time=now.time(),
            reason=reason,
            is_emergency=True,
            status='PENDING'
        )
        Admission.objects.create(
            patient=request.user,
            hospital=hospital,
            doctor=doctor_profile.user,
            appointment=apt,
            admission_time=now,
            notes=reason
        )

    messages.success(request, 'Emergency appointment booked successfully!')
    return redirect('appointments:history')


def cancel_appointment(request, pk):
    """Cancel appointment - release slot, restore bed if emergency"""
    if not request.user.is_authenticated or request.user.role != 'PATIENT':
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')

    appointment = get_object_or_404(Appointment, pk=pk, patient=request.user)

    if not appointment.can_be_cancelled():
        messages.error(request, 'This appointment cannot be cancelled.')
        return redirect('appointments:history')

    if request.method == 'POST':
        with transaction.atomic():
            if appointment.is_emergency and appointment.hospital:
                from hospitals.models import Admission
                admission = Admission.objects.filter(appointment=appointment).first()
                if admission and admission.discharge_time is None:
                    admission.discharge_time = timezone.now()
                    admission.save()
            appointment.status = 'CANCELLED'
            appointment.save()
        messages.success(request, 'Appointment cancelled successfully.')
    return redirect('appointments:history')
