from django.urls import path
from . import views

app_name = 'doctors'

urlpatterns = [
    path('search/', views.DoctorSearchView.as_view(), name='doctor_search'),
    path('<int:pk>/', views.DoctorDetailView.as_view(), name='doctor_detail'),
    path('request-join/<int:hospital_id>/', views.request_join_hospital, name='request_join_hospital'),
]
