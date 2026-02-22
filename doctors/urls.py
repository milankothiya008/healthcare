from django.urls import path
from . import views

app_name = 'doctors'

urlpatterns = [
    path('search/', views.DoctorSearchView.as_view(), name='doctor_search'),
    path('<int:pk>/', views.DoctorDetailView.as_view(), name='doctor_detail'),
    path('request-join/<int:hospital_id>/', views.request_join_hospital, name='request_join_hospital'),
    # Doctor dashboard (doctor role only)
    path('dashboard/hospitals/', views.DoctorHospitalListView.as_view(), name='doctor_hospital_list'),
    path('dashboard/request/<int:hospital_id>/', views.DoctorSendRequestView.as_view(), name='doctor_send_request'),
    path('dashboard/availability/', views.DoctorAvailabilityView.as_view(), name='doctor_availability'),
    path('dashboard/appointments/', views.DoctorAppointmentListView.as_view(), name='doctor_appointment_list'),
    path('dashboard/appointments/<int:pk>/', views.DoctorAppointmentDetailView.as_view(), name='doctor_appointment_detail'),
    path('dashboard/appointments/<int:pk>/approve/', views.doctor_appointment_approve, name='doctor_appointment_approve'),
    path('dashboard/appointments/<int:pk>/reject/', views.doctor_appointment_reject, name='doctor_appointment_reject'),
    path('dashboard/appointments/<int:pk>/complete/', views.doctor_appointment_complete, name='doctor_appointment_complete'),
    path('dashboard/appointments/<int:pk>/notes/', views.doctor_appointment_notes, name='doctor_appointment_notes'),
]
