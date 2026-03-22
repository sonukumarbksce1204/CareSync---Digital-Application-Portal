from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.patient_signup, name='patient_signup'),
    path('login/', views.patient_login, name='patient_login'),
    path('dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('logout/', views.patient_logout, name='patient_logout'),
    path('predict/', views.disease_predictor, name='disease_predictor'),
    path('symptom-suggestions/', views.symptom_suggestions, name='symptom_suggestions'),
    path('family/hub/', views.family_hub_view, name='patient_family_hub'),
    path('family/change-head/', views.change_head_view, name='change_family_head'),
    path('family/request-join/', views.request_join_family, name='request_join_family'),
    path('family/review-request/<int:req_id>/<str:action>/', views.review_join_request, name='review_join_request'),
    path('family/member/<int:member_id>/', views.member_history_view, name='member_history_view'),
    
    path('profile/', views.patient_profile, name='patient_profile'),
    path('hospitals/', views.hospitals_list, name='patient_hospitals'),
    path('hospitals/<int:hospital_id>/', views.hospital_detail, name='patient_hospital_detail'),
    path('doctors/', views.doctors_list, name='patient_doctors'),
    path('doctors/<uuid:doc_id>/', views.doctor_detail, name='patient_doctor_detail'),
    path('appointments/', views.appointments_view, name='patient_appointments'),
    path('appointments/book/', views.book_appointment, name='book_appointment'),
    path('appointments/cancel/<int:apt_id>/', views.cancel_appointment, name='cancel_appointment'),
    path('history/<int:symptom_id>/', views.symptom_detail, name='symptom_detail'),
    path('history/<int:symptom_id>/delete/', views.delete_symptom, name='delete_symptom'),
    path('privacy/', views.privacy_policy, name='privacy_policy'),
    path('contact/', views.contact_page, name='contact'),
]
