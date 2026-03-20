# from django.urls import path
# from . import views

# urlpatterns = [
#     path('signup/', views.doctor_signup, name='doctor_signup'),
#     # path('login/', views.doctor_login, name='doctor_login'),
#     # path('dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
#     # path('logout/', views.doctor_logout, name='doctor_logout'),
# ]
from django.urls import path
from .views import doctor_signup, doctor_login, doctor_dashboard, doctor_logout

urlpatterns = [
    path("signup/", doctor_signup, name="doctor_signup"),
    path("login/", doctor_login, name="doctor_login"),
    path("dashboard/", doctor_dashboard, name="doctor_dashboard"),
    path("logout/", doctor_logout, name="doctor_logout"),
]
