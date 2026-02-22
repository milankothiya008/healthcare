from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone

from .models import Hospital, HospitalReview
from accounts.mixins import PatientRequiredMixin
from appointments.models import Appointment


class HospitalSearchView(LoginRequiredMixin, ListView):
    """Search hospitals by name, city, or department (facilities)"""
    model = Hospital
    template_name = 'hospitals/hospital_search.html'
    context_object_name = 'hospitals'
    paginate_by = 10

    def get_queryset(self):
        qs = Hospital.objects.select_related('user').all()
        q = self.request.GET.get('q', '').strip()
        city = self.request.GET.get('city', '').strip()
        department = self.request.GET.get('department', '').strip()

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(address__icontains=q) |
                Q(city__icontains=q)
            )
        if city:
            qs = qs.filter(city__icontains=city)
        if department:
            qs = qs.filter(facilities__icontains=department)

        return qs.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_q'] = self.request.GET.get('q', '')
        context['search_city'] = self.request.GET.get('city', '')
        context['search_department'] = self.request.GET.get('department', '')
        return context


class HospitalDetailView(LoginRequiredMixin, DetailView):
    """Hospital detail with doctors and reviews"""
    model = Hospital
    template_name = 'hospitals/hospital_detail.html'
    context_object_name = 'hospital'

    def get_queryset(self):
        return Hospital.objects.select_related('user').prefetch_related('doctors__user', 'reviews__patient')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hospital = self.object
        context['doctors'] = hospital.doctors.select_related('user').filter(
            user__is_approved=True,
            user__is_active=True
        )
        context['reviews'] = hospital.reviews.select_related('patient').order_by('-created_at')[:20]

        # Can patient review? Only if they have completed appointment at this hospital
        can_review = False
        has_reviewed = False
        if self.request.user.is_authenticated and self.request.user.role == 'PATIENT':
            has_reviewed = hospital.reviews.filter(patient=self.request.user).exists()
            if not has_reviewed:
                can_review = Appointment.objects.filter(
                    patient=self.request.user,
                    hospital=hospital,
                    status='COMPLETED'
                ).exists()
        context['can_review'] = can_review
        context['has_reviewed'] = has_reviewed
        # Can doctor request to join?
        can_request_join = False
        if self.request.user.is_authenticated and self.request.user.role == 'DOCTOR' and self.request.user.is_approved:
            doc_profile = getattr(self.request.user, 'doctor_profile', None)
            if doc_profile and doc_profile.hospital_id != hospital.id:
                req = hospital.doctor_requests.filter(doctor=doc_profile).first()
                can_request_join = req is None or req.status == 'REJECTED'
        context['can_request_join'] = can_request_join
        return context


def submit_review(request, pk):
    """Submit hospital review - patient only, after completed appointment"""
    if not request.user.is_authenticated or request.user.role != 'PATIENT':
        messages.error(request, 'Permission denied.')
        return redirect('accounts:login')

    hospital = get_object_or_404(Hospital, pk=pk)

    # Check if already reviewed
    if hospital.reviews.filter(patient=request.user).exists():
        messages.warning(request, 'You have already reviewed this hospital.')
        return redirect('hospitals:hospital_detail', pk=pk)

    # Check if has completed appointment
    if not Appointment.objects.filter(patient=request.user, hospital=hospital, status='COMPLETED').exists():
        messages.error(request, 'You can only review a hospital after completing an appointment there.')
        return redirect('hospitals:hospital_detail', pk=pk)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '').strip()

        try:
            rating = int(rating)
            if 1 <= rating <= 5:
                HospitalReview.objects.create(
                    hospital=hospital,
                    patient=request.user,
                    rating=rating,
                    comment=comment
                )
                messages.success(request, 'Thank you for your review!')
            else:
                messages.error(request, 'Rating must be between 1 and 5.')
        except (ValueError, TypeError):
            messages.error(request, 'Invalid rating.')

    return redirect('hospitals:hospital_detail', pk=pk)
