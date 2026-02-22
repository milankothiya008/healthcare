from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    path('history/', views.AppointmentHistoryView.as_view(), name='history'),
    path('book/normal/<int:doctor_id>/', views.book_normal_appointment, name='book_normal'),
    path('book/emergency/', views.emergency_hospital_list, name='emergency_booking'),
    path('book/emergency/confirm/', views.confirm_emergency_booking, name='confirm_emergency'),
    path('cancel/<int:pk>/', views.cancel_appointment, name='cancel'),
]
