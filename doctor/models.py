import uuid
from django.db import models
from django.contrib.auth.hashers import make_password, check_password

class Specialization(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Doctor(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    )

    VERIFY_CHOICES = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )

    doctor_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, unique=True)

    password = models.CharField(max_length=255)

    experience_years = models.PositiveIntegerField()

    specializations = models.ManyToManyField(Specialization)

    profile_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    verification_status = models.CharField(max_length=10, choices=VERIFY_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
    def __str__(self):
        return self.full_name


class Qualification(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='qualifications')

    degree = models.CharField(max_length=100)
    institution = models.CharField(max_length=200)
    year_completed = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.degree} - {self.doctor.full_name}"


class DoctorVerification(models.Model):
    doctor = models.OneToOneField(Doctor, on_delete=models.CASCADE, related_name='verification')

    license_number = models.CharField(max_length=100, unique=True)
    license_document = models.FileField(upload_to='doctor_licenses/')

    verified_by_admin = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.license_number