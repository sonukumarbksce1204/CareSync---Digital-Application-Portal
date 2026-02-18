from django.db import models
from django.contrib.auth.models import User
import random

import string

def generate_patient_id():
    return ''.join(
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
        'Patient',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_family'
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
        related_name='members'
    )

    age = models.IntegerField(blank=True, null=True)

    gender = models.CharField(
        max_length=10,
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other')
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

    # Basic details
    description = models.TextField()
    address = models.TextField()

    # NEW FIELDS
    duration_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="How many days since symptoms started?"
    )

    medicines_taken = models.TextField(
        null=True,
        blank=True,
        help_text="Mention any medicines already taken"
    )

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

    # Image (like skin infection photo etc.)
    image = models.ImageField(
        upload_to='symptoms/',
        null=True,
        blank=True
    )

    # Test reports (PDF / image)
    test_report = models.FileField(
        upload_to='test_reports/',
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.user.username} - {self.created_at}"
