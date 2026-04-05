from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='admin_login'),
    path('signup/', views.signup_view, name='admin_signup'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('dashboard/', views.dashboard, name='admin_dashboard'),

    # Doctors
    path('doctors/', views.admin_doctors, name='admin_doctors'),
    path('doctors/<int:doctor_id>/edit/', views.admin_doctor_edit, name='admin_doctor_edit'),

    # Hospitals
    path('hospitals/', views.admin_hospitals, name='admin_hospitals'),
    path('hospitals/<int:hospital_id>/edit/', views.admin_hospital_edit, name='admin_hospital_edit'),

    # Patients
    path('patients/', views.admin_patients, name='admin_patients'),
    path('patients/<int:patient_id>/edit/', views.admin_patient_edit, name='admin_patient_edit'),

    # Disease & Specialists
    path('disease-mappings/', views.disease_mappings, name='admin_disease_mappings'),
    path('disease-mappings/delete/<int:mapping_id>/', views.delete_disease_mapping, name='admin_delete_disease_mapping'),
]
