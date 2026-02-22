from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    
    # Dashboard redirect
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),
    
    # Role-based dashboards
    path('admin/dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin/users/', views.AdminUserListView.as_view(), name='admin_user_list'),
    path('admin/patients/', views.AdminPatientListView.as_view(), name='admin_patient_list'),
    path('admin/doctors/', views.AdminDoctorListView.as_view(), name='admin_doctor_list'),
    path('admin/hospitals/', views.AdminHospitalListView.as_view(), name='admin_hospital_list'),
    path('admin/user/<int:pk>/', views.AdminUserProfileView.as_view(), name='admin_user_profile'),
    path('admin/doctor-profile-requests/', views.AdminDoctorProfileUpdateRequestListView.as_view(), name='admin_doctor_profile_requests'),
    path('admin/doctor-profile-request/<int:pk>/approve/', views.admin_approve_doctor_profile_request, name='admin_approve_doctor_profile_request'),
    path('admin/doctor-profile-request/<int:pk>/reject/', views.admin_reject_doctor_profile_request, name='admin_reject_doctor_profile_request'),
    path('doctor/dashboard/', views.DoctorDashboardView.as_view(), name='doctor_dashboard'),
    path('doctor/profile/edit/', views.DoctorProfileEditView.as_view(), name='doctor_profile_edit'),
    path('doctor/profile/photo/', views.DoctorProfilePhotoUploadView.as_view(), name='doctor_profile_photo'),
    path('patient/dashboard/', views.PatientDashboardView.as_view(), name='patient_dashboard'),
    path('hospital/dashboard/', views.HospitalDashboardView.as_view(), name='hospital_dashboard'),
    
    # Approval actions
    path('admin/approve-doctor/<int:user_id>/', views.approve_doctor, name='approve_doctor'),
    path('admin/approve-hospital/<int:user_id>/', views.approve_hospital, name='approve_hospital'),
    path('admin/reject-doctor/<int:user_id>/', views.reject_doctor, name='reject_doctor'),
    path('admin/reject-hospital/<int:user_id>/', views.reject_hospital, name='reject_hospital'),
    
    # Block/Unblock actions
    path('admin/block-user/<int:user_id>/', views.block_user, name='block_user'),
    path('admin/unblock-user/<int:user_id>/', views.unblock_user, name='unblock_user'),
]
