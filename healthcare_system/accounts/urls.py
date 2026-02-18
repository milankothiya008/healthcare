from django.urls import path
from .views import register_view

from .views import *

urlpatterns = [
    path("register/", register_view, name="register"),
    path("login/", login_view, name="login"),
    path("patient/", patient_dashboard, name="patient_dashboard"),
    path("doctor/", doctor_dashboard, name="doctor_dashboard"),
    path("hospital/", hospital_dashboard, name="hospital_dashboard"),
    path("admin/", admin_dashboard, name="admin_dashboard"),
    path("admin/", admin_dashboard, name="admin_dashboard"),

    path("approve-doctor/<int:doctor_id>/", approve_doctor, name="approve_doctor"),
    path("reject-doctor/<int:doctor_id>/", reject_doctor, name="reject_doctor"),

    path("approve-hospital/<int:hospital_id>/", approve_hospital, name="approve_hospital"),
    path("reject-hospital/<int:hospital_id>/", reject_hospital, name="reject_hospital"),
    path("doctor-detail/<int:doctor_id>/", doctor_detail, name="doctor_detail"),
    path("hospital-detail/<int:hospital_id>/", hospital_detail, name="hospital_detail"),

]