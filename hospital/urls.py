from django.urls import path
from . import views
from .views import hospital_patient_detail_view

urlpatterns = [
    path('signup/', views.hospital_register, name='hospital_register'),
    path('success/', views.hospital_success, name='hospital_success'),
    path('login/',views.hospital_login, name='hospital_login'),
    path("dashboard/", views.hospital_dashboard, name="hospital_dashboard"),
    path('search/', views.hospital_search_view, name='hospital_search'),
    path('patient/<str:patient_id>/', hospital_patient_detail_view, name='hospital_patient_detail'),
]
