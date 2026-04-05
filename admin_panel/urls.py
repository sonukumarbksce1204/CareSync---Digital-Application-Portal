from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='admin_login'),
    path('signup/', views.signup_view, name='admin_signup'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('dashboard/', views.dashboard, name='admin_dashboard'),
    path('doctors/', views.admin_doctors, name='admin_doctors'),
    path('hospitals/', views.admin_hospitals, name='admin_hospitals'),
    path('patients/', views.admin_patients, name='admin_patients'),
]
