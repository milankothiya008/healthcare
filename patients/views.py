from django.shortcuts import render, redirect
from django.views.generic import UpdateView
from django.contrib import messages
from django.urls import reverse_lazy

from .models import PatientProfile
from .forms import PatientProfileForm
from accounts.mixins import PatientRequiredMixin


class PatientProfileEditView(PatientRequiredMixin, UpdateView):
    """Edit patient profile and user details"""
    model = PatientProfile
    form_class = PatientProfileForm
    template_name = 'patients/profile_edit.html'
    success_url = reverse_lazy('patients:profile_edit')

    def get_object(self, queryset=None):
        return getattr(self.request.user, 'patient_profile', None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.get_object()
        return context

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj:
            messages.error(request, 'Patient profile not found.')
            return redirect('accounts:patient_dashboard')
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj:
            return redirect('accounts:patient_dashboard')

        form = PatientProfileForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect(self.success_url)
        return self.render_to_response(self.get_context_data(form=form))
