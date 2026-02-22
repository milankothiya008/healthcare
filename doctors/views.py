from datetime import time, timedelta, datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.http import JsonResponse

from .models import DoctorProfile
from appointments.models import Appointment


class DoctorSearchView(LoginRequiredMixin, ListView):
    """Search doctors - only approved doctors with hospital association"""
    model = DoctorProfile
    template_name = 'doctors/doctor_search.html'
    context_object_name = 'doctors'
    paginate_by = 10

    def get_queryset(self):
        # Only approved doctors assigned to at least one hospital
        qs = DoctorProfile.objects.select_related('user', 'hospital').filter(
            user__is_approved=True,
            user__is_active=True,
            hospital__isnull=False  # Must have hospital
        )
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
            qs = qs.filter(hospital__name__icontains=hospital_name)

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

        # Generate next 14 days as available dates
        available_dates = []
        for i in range(14):
            d = today + timedelta(days=i)
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
        """Generate time slots within doctor's schedule, excluding already booked"""
        today = timezone.now().date()
        now_time = timezone.now().time()

        # Get booked slots for this doctor on this date
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
