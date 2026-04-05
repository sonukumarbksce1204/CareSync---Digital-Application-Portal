from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class AdminUser(models.Model):
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.username


class DiseaseSpecialtyMapping(models.Model):
    disease_name = models.CharField(max_length=200, unique=True, help_text="Name of the disease as output by the PredictaCare AI.")
    specialty_name = models.CharField(max_length=200, help_text="Which doctor specialty to consult for this disease (e.g. Dermatologist).")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.disease_name} -> {self.specialty_name}"
