from django.db import models
from django.contrib.auth.models import User
import random
import string


def generate_patient_id():
    return "".join(
        random.choices(string.ascii_uppercase + string.digits, k=4)
    )


def generate_family_code():
    return str(random.randint(100000, 999999))


class Family(models.Model):
    family_id = models.CharField(
        max_length=6,
        unique=True,
        default=generate_family_code
    )

    created_at = models.DateTimeField(auto_now_add=True)

    head = models.ForeignKey(
        "Patient",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_family"
    )

    def __str__(self):
        return self.family_id


class Patient(models.Model):
    patient_id = models.CharField(
        max_length=4,
        unique=True,
        default=generate_patient_id,
        editable=False
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)

    family = models.ForeignKey(
        Family,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members"
    )

    age = models.IntegerField(blank=True, null=True)

    gender = models.CharField(
        max_length=10,
        choices=[
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
        ],
        blank=True
    )

    blood_group = models.CharField(
        max_length=5,
        blank=True
    )

    phone = models.CharField(
        max_length=15,
        blank=True
    )

    emergency_contact = models.CharField(
        max_length=15,
        blank=True
    )

    address = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient_id} - {self.user.username}"


class Symptom(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='symptoms'
    )

    description = models.TextField()
    address = models.TextField()

    duration_days = models.PositiveIntegerField(null=True, blank=True)
    medicines_taken = models.TextField(null=True, blank=True)

    improvement = models.CharField(
        max_length=50,
        choices=[
            ('better', 'Feeling Better'),
            ('same', 'No Improvement'),
            ('worse', 'Condition Worsening')
        ],
        null=True,
        blank=True
    )

    image = models.ImageField(upload_to='symptoms/', null=True, blank=True)
    test_report = models.FileField(upload_to='test_reports/', null=True, blank=True)

    predicted_disease = models.CharField(max_length=200, null=True, blank=True)
    prediction_confidence = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.user.username} - {self.created_at}"