from django.urls import path
from . import views

app_name = 'hospitals'

urlpatterns = [
    path('search/', views.HospitalSearchView.as_view(), name='hospital_search'),
    path('<int:pk>/', views.HospitalDetailView.as_view(), name='hospital_detail'),
    path('<int:pk>/review/', views.submit_review, name='submit_review'),
]
