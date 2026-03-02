from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from .models import Appointment
from doctors.models import DoctorProfile
from hospitals.models import Hospital, DoctorHospitalAssignment
from accounts.mixins import PatientRequiredMixin
from documents.models import Document


class AppointmentHistoryView(PatientRequiredMixin, ListView):
    """Patient appointment history - upcoming and past"""
    model = Appointment
    template_name = 'appointments/appointment_history.html'
    context_object_name = 'appointments'
    paginate_by = 15

    def get_queryset(self):
        """Return appointments filtered by tab, using consistent categorisation."""
        tab = self.request.GET.get('tab', 'upcoming')
        qs = Appointment.objects.filter(patient=self.request.user).select_related(
            'doctor', 'hospital', 'doctor__doctor_profile'
        ).order_by('-appointment_date', '-appointment_time')

        today = timezone.now().date()

        if tab == 'cancelled':
            return qs.filter(status='CANCELLED')

        if tab == 'past':
            # Past = strictly before today OR explicitly completed
            return qs.filter(
                Q(appointment_date__lt=today) | Q(status='COMPLETED')
            )

        if tab == 'today':
            return qs.filter(appointment_date=today)

        # Default: upcoming
        return qs.filter(
            appointment_date__gt=today,
            status__in=['PENDING', 'CONFIRMED']
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        base_qs = Appointment.objects.filter(patient=self.request.user)

        context['tab'] = self.request.GET.get('tab', 'upcoming')
        context['past_count'] = base_qs.filter(
            Q(appointment_date__lt=today) | Q(status='COMPLETED')
        ).count()
        context['upcoming_count'] = base_qs.filter(
            appointment_date__gt=today,
            status__in=['PENDING', 'CONFIRMED']
        ).count()
        context['today_count'] = base_qs.filter(appointment_date=today).count()
        context['cancelled_count'] = base_qs.filter(status='CANCELLED').count()
        return context


def book_normal_appointment(request, doctor_id):
    """Book normal appointment - select hospital, date, time slot"""
    if not request.user.is_authenticated or request.user.role != 'PATIENT':
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')

    doctor = get_object_or_404(DoctorProfile, pk=doctor_id, user__is_approved=True, user__is_active=True)
    # Hospitals where doctor works (legacy + assignments)
    doctor_hospital_ids = set()
    if doctor.hospital_id:
        doctor_hospital_ids.add(doctor.hospital_id)
    doctor_hospital_ids.update(
        DoctorHospitalAssignment.objects.filter(doctor=doctor, is_active=True).values_list('hospital_id', flat=True)
    )
    if not doctor_hospital_ids:
        messages.error(request, 'This doctor is not associated with any hospital.')
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

        # If booking for today, time must be in the future
        if not errors and appointment_date == today:
            now_time = timezone.now().time()
            if appointment_time <= now_time:
                errors.append('Cannot book a time that has already passed. Please choose a later time today.')

        hospital = None
        if hospital_id:
            try:
                hid = int(hospital_id)
                if hid not in doctor_hospital_ids:
                    errors.append('Invalid hospital selection.')
                else:
                    hospital = Hospital.objects.get(pk=hid)
            except (ValueError, Hospital.DoesNotExist):
                errors.append('Invalid hospital selection.')
        else:
            hospital = Hospital.objects.filter(pk__in=doctor_hospital_ids).first()

        if errors:
            for e in errors:
                messages.error(request, e)
            return redirect('appointments:book_normal', doctor_id=doctor_id)

        # Check double booking (global across hospitals)
        if Appointment.objects.filter(
            doctor=doctor.user,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status__in=['PENDING', 'CONFIRMED']
        ).exists():
            messages.error(request, 'This time slot is already booked.')
            return redirect('appointments:book_normal', doctor_id=doctor_id)

        appointment = Appointment.objects.create(
            patient=request.user,
            doctor=doctor.user,
            hospital=hospital,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            reason=reason,
            is_emergency=False,
            status='PENDING'
        )
        # Optional: patient uploaded medical reports during booking
        files = request.FILES.getlist('reports')
        for f in files:
            # Basic validation is handled in Document model / storage, but keep type guard here
            name_lower = (f.name or '').lower()
            if not (name_lower.endswith('.pdf') or name_lower.endswith('.jpg') or name_lower.endswith('.jpeg') or name_lower.endswith('.png')):
                messages.warning(request, f'Skipped unsupported file type: {f.name}')
                continue
            if f.size and f.size > 10 * 1024 * 1024:  # 10 MB limit
                messages.warning(request, f'Skipped file over 10 MB: {f.name}')
                continue
            Document.objects.create(
                patient=request.user,
                doctor=doctor.user,
                hospital=hospital,
                appointment=appointment,
                document_type='OTHER',
                title=f.name,
                file=f,
                uploaded_by=request.user,
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
    doctor_profile = hospital.get_doctors().filter(user__is_approved=True, user__is_active=True).first()
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


class PatientAppointmentDetailView(PatientRequiredMixin, DetailView):
    """Detailed view of a patient's own appointment.

    Full medical details (notes, prescription, attached reports) are only
    visible once the appointment has been marked COMPLETED.
    """
    model = Appointment
    template_name = 'appointments/patient_appointment_detail.html'
    context_object_name = 'appointment'

    def get_queryset(self):
        # Restrict strictly to the logged‑in patient
        return Appointment.objects.filter(patient=self.request.user).select_related(
            'doctor', 'hospital'
        )

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Allow detail page only for completed / past appointments
        if self.object.status != 'COMPLETED':
            messages.error(request, 'Details are available only after the appointment is completed.')
            return redirect('appointments:history')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        apt = self.object
        # Documents linked to this appointment (patient or doctor uploaded)
        context['appointment_documents'] = Document.objects.filter(
            appointment=apt,
            patient=self.request.user
        ).select_related('doctor', 'hospital')
        # Flags for template visibility
        context['can_view_medical_details'] = apt.status == 'COMPLETED'
        return context


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
