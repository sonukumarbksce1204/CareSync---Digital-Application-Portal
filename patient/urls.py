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
]
