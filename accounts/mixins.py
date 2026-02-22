from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


class RoleRequiredMixin(LoginRequiredMixin):
    """Mixin to require specific role(s) for access"""
    allowed_roles = []
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Check if user account is blocked
        if not request.user.is_active:
            from django.contrib.auth import logout
            logout(request)
            messages.error(request, 'Your account has been blocked. Please contact the administrator.')
            return redirect('accounts:login')
        
        if request.user.role not in self.allowed_roles:
            messages.error(request, "You don't have permission to access this page.")
            return redirect('accounts:dashboard_redirect')
        
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(RoleRequiredMixin):
    """Mixin to require Admin role"""
    allowed_roles = ['ADMIN']


class DoctorRequiredMixin(RoleRequiredMixin):
    """Mixin to require Doctor role"""
    allowed_roles = ['DOCTOR']
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_approved:
            messages.warning(request, "Your account is pending approval. Please wait for admin approval.")
            return redirect('accounts:dashboard_redirect')
        return super().dispatch(request, *args, **kwargs)


class PatientRequiredMixin(RoleRequiredMixin):
    """Mixin to require Patient role"""
    allowed_roles = ['PATIENT']


class HospitalRequiredMixin(RoleRequiredMixin):
    """Mixin to require Hospital Admin role - only own hospital data"""
    allowed_roles = ['HOSPITAL', 'HOSPITAL_ADMIN']
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_approved:
            messages.warning(request, "Your account is pending approval. Please wait for admin approval.")
            return redirect('accounts:dashboard_redirect')
        return super().dispatch(request, *args, **kwargs)


class ApprovedUserMixin(LoginRequiredMixin):
    """Mixin to ensure user is approved (for Doctors and Hospitals)"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Admin and Patient don't need approval
        if request.user.role in ['DOCTOR', 'HOSPITAL'] and not request.user.is_approved:
            messages.warning(request, "Your account is pending approval. Please wait for admin approval.")
            return redirect('accounts:dashboard_redirect')
        
        return super().dispatch(request, *args, **kwargs)
