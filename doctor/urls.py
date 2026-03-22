# from django.urls import path
# from . import views

# urlpatterns = [
#     path('signup/', views.doctor_signup, name='doctor_signup'),
#     # path('login/', views.doctor_login, name='doctor_login'),
#     # path('dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
#     # path('logout/', views.doctor_logout, name='doctor_logout'),
# ]
from django.urls import path
from .views import (
    doctor_profile, doctor_signup, doctor_login, doctor_dashboard, doctor_logout, 
    doctor_search_view, doctor_patient_detail_view, review_prediction,
    doctor_appointments, update_appointment_status, my_patients, pending_reviews,
    add_consultation, hospital_affiliations
)

urlpatterns = [
    path("signup/", doctor_signup, name="doctor_signup"),
    path("login/", doctor_login, name="doctor_login"),
    path("dashboard/", doctor_dashboard, name="doctor_dashboard"),
    path("logout/", doctor_logout, name="doctor_logout"),
    path("profile/", doctor_profile, name="doctor_profile"),
    path("search/", doctor_search_view, name="doctor_search"),
    path("patient/<str:patient_id>/", doctor_patient_detail_view, name="doctor_patient_detail"),
    path("patient/review/<int:symptom_id>/", review_prediction, name="review_prediction"),
    
    # New Workspace Routes
    path("appointments/", doctor_appointments, name="doctor_appointments"),
    path("appointments/<int:apt_id>/<str:target_status>/", update_appointment_status, name="update_appointment_status"),
    path("my-patients/", my_patients, name="my_patients"),
    path("pending-reviews/", pending_reviews, name="pending_reviews"),
    path("patient/<str:patient_id>/consultation/", add_consultation, name="add_consultation"),
    path("affiliations/", hospital_affiliations, name="hospital_affiliations"),
]
