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

    family_relationship = models.CharField(
        max_length=20,
        choices=[
            ('HEAD', 'Head'), ('SPOUSE', 'Spouse'), ('SON', 'Son'), ('DAUGHTER', 'Daughter'),
            ('FATHER', 'Father'), ('MOTHER', 'Mother'), ('BROTHER', 'Brother'), ('SISTER', 'Sister'),
            ('GRANDFATHER', 'Grandfather'), ('GRANDMOTHER', 'Grandmother'),
            ('GUARDIAN', 'Guardian'), ('OTHER', 'Other')
        ],
        blank=True, null=True
    )
    is_deceased = models.BooleanField(default=False)

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

    is_archived = models.BooleanField(default=False)
    
    AI_STATUS_CHOICES = [
        ('PENDING_REVIEW', 'Pending Review'),
        ('APPROVED', 'Approved by Doctor'),
        ('MODIFIED', 'Modified by Doctor'),
        ('REJECTED', 'Rejected by Doctor')
    ]
    ai_prediction_status = models.CharField(max_length=20, choices=AI_STATUS_CHOICES, default='PENDING_REVIEW')
    doctor_final_diagnosis_catalog = models.ForeignKey('patient.DiseaseCatalog', on_delete=models.SET_NULL, null=True, blank=True)
    doctor_modified_diagnosis_text = models.CharField(max_length=255, null=True, blank=True)
    doctor_diagnosis_notes = models.CharField(max_length=255, null=True, blank=True)
    verified_by_doctor = models.ForeignKey('doctor.Doctor', on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_symptoms')
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_note = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.user.username} - {self.created_at}"


def prescription_upload_path(instance, filename):
    import uuid
    import os
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('prescriptions', filename)

class ConsultationRecord(models.Model):
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE, related_name='consultations')
    doctor = models.ForeignKey('doctor.Doctor', on_delete=models.SET_NULL, null=True, related_name='consultations')
    appointment = models.OneToOneField('Appointment', on_delete=models.SET_NULL, null=True, blank=True, related_name='consultation')
    
    diagnosis_text = models.CharField(max_length=255, null=True, blank=True)
    notes = models.TextField(help_text="Clinical observations and advice.")
    doctor_instructions = models.TextField(null=True, blank=True)
    
    prescription_document = models.FileField(upload_to=prescription_upload_path, null=True, blank=True)
    
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_note = models.TextField(null=True, blank=True)
    
    consultation_type = models.CharField(max_length=50, null=True, blank=True)
    is_finalized = models.BooleanField(default=True)
    created_by_ai_review = models.BooleanField(default=False)
    visible_to_patient = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Consultation on {self.created_at.date()} for {self.patient.patient_id}"


class DiseaseCatalog(models.Model):
    name = models.CharField(max_length=150)
    is_hereditary = models.BooleanField(default=False)
    icd_code = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.name


class PatientDisease(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='diseases')
    disease = models.ForeignKey(DiseaseCatalog, on_delete=models.CASCADE)
    diagnosed_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)


class DoctorAccessLog(models.Model):
    ACCESS_TYPES = [
        ('PERSONAL', 'Personal ID'),
        ('FAMILY', 'Family ID'),
        ('EXPANDED', 'Expanded from Personal')
    ]
    doctor = models.ForeignKey('doctor.Doctor', on_delete=models.CASCADE, related_name='doctor_accesses')
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True)
    family = models.ForeignKey(Family, on_delete=models.SET_NULL, null=True, blank=True)
    access_method = models.CharField(max_length=20, choices=ACCESS_TYPES)
    accessed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dr. {self.doctor} accessed {self.access_method}"



class FamilyHeadChangeLog(models.Model):
    family = models.ForeignKey(Family, on_delete=models.CASCADE)
    old_head = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, related_name='old_head_logs')
    new_head = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, related_name='new_head_logs')
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Head changed to {self.new_head}"


class FamilyJoinRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected')
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='sent_join_requests')
    family = models.ForeignKey(Family, on_delete=models.CASCADE, related_name='join_requests')
    
    requested_relationship = models.CharField(
        max_length=20, 
        choices=[
            ('HEAD', 'Head'), ('SPOUSE', 'Spouse'), ('SON', 'Son'), ('DAUGHTER', 'Daughter'),
            ('FATHER', 'Father'), ('MOTHER', 'Mother'), ('BROTHER', 'Brother'), ('SISTER', 'Sister'),
            ('GRANDFATHER', 'Grandfather'), ('GRANDMOTHER', 'Grandmother'),
            ('GUARDIAN', 'Guardian'), ('OTHER', 'Other')
        ]
    )
    custom_relationship = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_join_requests')

    class Meta:
        unique_together = ('patient', 'family', 'status')

    def __str__(self):
        return f"{self.patient.user.username} -> {self.family.family_id} ({self.status})"


class HospitalAccessLog(models.Model):
    ACCESS_TYPES = [
        ('PERSONAL', 'Personal ID'),
        ('FAMILY', 'Family ID'),
        ('EXPANDED', 'Expanded from Personal')
    ]
    hospital = models.ForeignKey('hospital.Hospital', on_delete=models.CASCADE, related_name='hospital_accesses')
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True)
    family = models.ForeignKey(Family, on_delete=models.SET_NULL, null=True, blank=True)
    access_method = models.CharField(max_length=20, choices=ACCESS_TYPES)
    accessed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.hospital} accessed {self.access_method}"

class AIReviewLog(models.Model):
    symptom = models.ForeignKey(Symptom, on_delete=models.CASCADE, related_name='review_logs')
    doctor = models.ForeignKey('doctor.Doctor', on_delete=models.CASCADE)
    previous_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    
    previous_diagnosis_text = models.CharField(max_length=200, null=True, blank=True)
    new_diagnosis_text = models.CharField(max_length=200, null=True, blank=True)
    previous_catalog_id = models.IntegerField(null=True, blank=True)
    new_catalog_id = models.IntegerField(null=True, blank=True)
    
    note = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dr. {self.doctor} changed {self.symptom} to {self.new_status}"

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('REQUESTED', 'Requested'),
        ('APPROVED', 'Approved'),
        ('IN_CONSULTATION', 'In Consultation'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('REJECTED', 'Rejected'),
    ]
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey('doctor.Doctor', on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments')
    hospital = models.ForeignKey('hospital.Hospital', on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments')
    
    preferred_date = models.DateField()
    appointment_time = models.TimeField(null=True, blank=True)
    
    reason = models.TextField()
    note = models.TextField(blank=True, null=True)
    
    doctor_instructions = models.TextField(null=True, blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='REQUESTED')
    
    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    rejection_reason = models.TextField(null=True, blank=True)
    cancellation_reason = models.TextField(null=True, blank=True)
    visit_mode = models.CharField(max_length=50, null=True, blank=True, choices=[('IN_PERSON', 'In Person'), ('ONLINE', 'Online')])
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Apt: {self.patient} on {self.preferred_date}"