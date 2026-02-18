from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.patient_signup, name='patient_signup'),
    path('login/', views.patient_login, name='patient_login'),
    path('dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('logout/', views.patient_logout, name='patient_logout'),
]
