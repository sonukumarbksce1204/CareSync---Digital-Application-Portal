from django.db import models
from django.contrib.auth.hashers import make_password

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Hospital(models.Model):
    HOSPITAL_TYPES = [
        ('Government', 'Government'),
        ('Private', 'Private'),
        ('Trust', 'Trust'),
    ]

    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=100, unique=True)
    hospital_type = models.CharField(max_length=100, choices=HOSPITAL_TYPES)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    contact_number = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    website = models.URLField(blank=True, null=True)
    established_year = models.PositiveIntegerField(blank=True, null=True)
    total_beds = models.PositiveIntegerField(default=0)
    emergency_services = models.BooleanField(default=False)
    password = models.CharField(max_length=255, null=True, blank=True)

    registration_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # If password is not already hashed, hash it before saving
        if not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.city})"


class HospitalImage(models.Model):
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='hospital_gallery/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image of {self.hospital.name}"


class HospitalClosure(models.Model):
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='closures')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.hospital.name} Closure: {self.start_date} to {self.end_date}"
