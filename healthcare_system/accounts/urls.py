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
]