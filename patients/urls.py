from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('profile/', views.PatientProfileEditView.as_view(), name='profile_edit'),
]
