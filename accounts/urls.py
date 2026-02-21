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
    path('doctor/dashboard/', views.DoctorDashboardView.as_view(), name='doctor_dashboard'),
    path('patient/dashboard/', views.PatientDashboardView.as_view(), name='patient_dashboard'),
    path('hospital/dashboard/', views.HospitalDashboardView.as_view(), name='hospital_dashboard'),
    
    # Approval actions
    path('admin/approve-doctor/<int:user_id>/', views.approve_doctor, name='approve_doctor'),
    path('admin/approve-hospital/<int:user_id>/', views.approve_hospital, name='approve_hospital'),
    path('admin/reject-doctor/<int:user_id>/', views.reject_doctor, name='reject_doctor'),
    path('admin/reject-hospital/<int:user_id>/', views.reject_hospital, name='reject_hospital'),
]
