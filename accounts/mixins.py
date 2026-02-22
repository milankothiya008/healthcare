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
    """Mixin to require Doctor role - explicit role check so e.g. Hospital Admin cannot access doctor pages"""
    allowed_roles = ['DOCTOR']

    def dispatch(self, request, *args, **kwargs):
        # 1) Parent checks is_authenticated and role in allowed_roles (redirects if not)
        result = super().dispatch(request, *args, **kwargs)
        # 2) Explicit role check: only DOCTOR may access (defense in depth; blocks e.g. hospital user)
        if request.user.is_authenticated and getattr(request.user, 'role', None) != 'DOCTOR':
            messages.error(request, "You don't have permission to access this page.")
            return redirect('accounts:dashboard_redirect')
        # 3) Doctor must be approved
        if request.user.is_authenticated and not getattr(request.user, 'is_approved', True):
            messages.warning(request, "Your account is pending approval. Please wait for admin approval.")
            return redirect('accounts:dashboard_redirect')
        return result


class PatientRequiredMixin(RoleRequiredMixin):
    """Mixin to require Patient role"""
    allowed_roles = ['PATIENT']


class HospitalRequiredMixin(RoleRequiredMixin):
    """Mixin to require Hospital Admin role - explicit check so e.g. Doctor cannot access hospital admin pages"""
    allowed_roles = ['HOSPITAL', 'HOSPITAL_ADMIN']

    def dispatch(self, request, *args, **kwargs):
        result = super().dispatch(request, *args, **kwargs)
        if request.user.is_authenticated and getattr(request.user, 'role', None) not in ('HOSPITAL', 'HOSPITAL_ADMIN'):
            messages.error(request, "You don't have permission to access this page.")
            return redirect('accounts:dashboard_redirect')
        if request.user.is_authenticated and not getattr(request.user, 'is_approved', True):
            messages.warning(request, "Your account is pending approval. Please wait for admin approval.")
            return redirect('accounts:dashboard_redirect')
        return result


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
