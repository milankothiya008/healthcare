from django.urls import path
from . import views
from . import admin_views

app_name = 'hospitals'

urlpatterns = [
    path('search/', views.HospitalSearchView.as_view(), name='hospital_search'),
    path('<int:pk>/', views.HospitalDetailView.as_view(), name='hospital_detail'),
    path('<int:pk>/review/', views.submit_review, name='submit_review'),
    # Hospital Admin (HOSPITAL/HOSPITAL_ADMIN role only)
    path('admin/', admin_views.HospitalAdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin/profile/', admin_views.HospitalProfileEditView.as_view(), name='admin_profile'),
    path('admin/doctors/requests/', admin_views.DoctorRequestListView.as_view(), name='admin_doctor_requests'),
    path('admin/doctors/requests/<int:pk>/', admin_views.DoctorRequestDetailView.as_view(), name='admin_doctor_request_detail'),
    path('admin/doctors/requests/<int:pk>/approve/', admin_views.approve_doctor_request, name='admin_approve_doctor_request'),
    path('admin/doctors/requests/<int:pk>/reject/', admin_views.reject_doctor_request, name='admin_reject_doctor_request'),
    path('admin/doctors/', admin_views.HospitalDoctorListView.as_view(), name='admin_doctor_list'),
    path('admin/doctors/<int:pk>/', admin_views.HospitalDoctorDetailView.as_view(), name='admin_doctor_detail'),
    path('admin/doctors/<int:pk>/remove/', admin_views.remove_doctor, name='admin_remove_doctor'),
    path('admin/appointments/', admin_views.HospitalAppointmentListView.as_view(), name='admin_appointments'),
    path('admin/appointments/<int:pk>/status/', admin_views.update_appointment_status, name='admin_update_appointment_status'),
    path('admin/admissions/', admin_views.AdmissionListView.as_view(), name='admin_admissions'),
    path('admin/admissions/admit/', admin_views.admit_patient, name='admin_admit_patient'),
    path('admin/admissions/<int:pk>/discharge/', admin_views.discharge_patient, name='admin_discharge_patient'),
]
