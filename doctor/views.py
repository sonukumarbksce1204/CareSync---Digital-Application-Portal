from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone

from .models import Doctor, Specialization, DoctorVerification, Qualification, HospitalAffiliation
from .forms import DoctorProfileUpdateForm, ConsultationForm, AIReviewForm

from patient.models import (
    Appointment, Patient, Family, Symptom,
    DoctorAccessLog, AIReviewLog, ConsultationRecord, PatientDisease, DiseaseCatalog
)
from patient.services.access_service import log_doctor_access
from patient.services.family_service import get_family_disease_summary
from hospital.models import Hospital


# ── Session Helper ────────────────────────────────────────────────────────────

def get_session_doctor(request):
    doctor_id = request.session.get("doctor_id")
    if not doctor_id:
        return None
    return Doctor.objects.filter(doctor_id=doctor_id).first()


# ── Signup ────────────────────────────────────────────────────────────────────

def doctor_signup(request):
    specializations = Specialization.objects.all()

    if request.method == "POST":
        full_name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        experience = request.POST.get("experience")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        license_number = request.POST.get("license_number")
        license_file = request.FILES.get("license_file")
        qualification_text = request.POST.get("qualification")
        selected_specs = request.POST.getlist("specializations")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return render(request, "doctor/signup.html", {"specializations": specializations})

        if Doctor.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return render(request, "doctor/signup.html", {"specializations": specializations})

        if Doctor.objects.filter(phone=phone).exists():
            messages.error(request, "Phone number already registered")
            return render(request, "doctor/signup.html", {"specializations": specializations})

        if DoctorVerification.objects.filter(license_number=license_number).exists():
            messages.error(request, "License number already registered")
            return render(request, "doctor/signup.html", {"specializations": specializations})

        doctor = Doctor(full_name=full_name, email=email, phone=phone, experience_years=experience)
        doctor.set_password(password)
        doctor.save()
        doctor.specializations.set(selected_specs)

        DoctorVerification.objects.create(
            doctor=doctor,
            license_number=license_number,
            license_document=license_file
        )

        if qualification_text:
            Qualification.objects.create(
                doctor=doctor,
                degree=qualification_text,
                institution="Not Provided",
                year_completed=2024
            )

        messages.success(request, "Signup successful. Wait for admin verification.")
        return redirect("doctor_signup")

    return render(request, "doctor/signup.html", {"specializations": specializations})


# ── Login / Logout ────────────────────────────────────────────────────────────

def doctor_login(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            doctor = Doctor.objects.get(email=email)
            if doctor.verification_status != "verified":
                messages.error(request, "Your account is not verified by admin.")
                return redirect("doctor_login")
            if doctor.check_password(password):
                request.session["doctor_id"] = str(doctor.doctor_id)
                return redirect("doctor_dashboard")
            else:
                messages.error(request, "Invalid password")
        except Doctor.DoesNotExist:
            messages.error(request, "Doctor not found")

    return render(request, "doctor/login.html")


def doctor_logout(request):
    request.session.flush()
    return redirect("doctor_login")


# ── Dashboard ─────────────────────────────────────────────────────────────────

def doctor_dashboard(request):
    doctor = get_session_doctor(request)
    if not doctor:
        request.session.flush()
        return redirect("doctor_login")

    pending_appointments = Appointment.objects.filter(doctor=doctor, status='REQUESTED').count()
    upcoming_appointments = Appointment.objects.filter(
        doctor=doctor, status='APPROVED', preferred_date__gte=timezone.now().date()
    ).count()

    accessed_patient_ids = DoctorAccessLog.objects.filter(doctor=doctor).values_list('patient_id', flat=True)
    apt_patient_ids = Appointment.objects.filter(
        doctor=doctor, status__in=['APPROVED', 'COMPLETED']
    ).values_list('patient_id', flat=True)
    my_patients_count = Patient.objects.filter(
        Q(id__in=accessed_patient_ids) | Q(id__in=apt_patient_ids)
    ).distinct().count()

    pending_reviews_count = Symptom.objects.filter(
        patient__id__in=accessed_patient_ids, ai_prediction_status='PENDING_REVIEW'
    ).count()

    return render(request, "doctor/dashboard.html", {
        "doctor": doctor,
        "pending_appointments": pending_appointments,
        "upcoming_appointments": upcoming_appointments,
        "my_patients_count": my_patients_count,
        "pending_reviews_count": pending_reviews_count,
    })


# ── Profile ───────────────────────────────────────────────────────────────────

def doctor_profile(request):
    doctor = get_session_doctor(request)
    if not doctor:
        request.session.flush()
        return redirect("doctor_login")

    if request.method == "POST":
        form = DoctorProfileUpdateForm(request.POST, request.FILES, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('doctor_profile')
    else:
        form = DoctorProfileUpdateForm(instance=doctor)

    return render(request, "doctor/profile.html", {
        "doctor": doctor,
        "form": form,
        "qualifications": doctor.qualifications.all(),
        "specializations": doctor.specializations.all(),
        "affiliations": doctor.affiliations.filter(status='APPROVED'),
    })


# ── Patient Search ────────────────────────────────────────────────────────────

def doctor_search_view(request):
    doctor = get_session_doctor(request)
    if not doctor:
        request.session.flush()
        return redirect("doctor_login")

    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type')

    if query:
        if search_type == 'family':
            family = Family.objects.filter(family_id=query).first()
            if family:
                log_doctor_access(doctor, 'FAMILY', family=family)
                summary = get_family_disease_summary(family)
                return render(request, 'doctor/family_result.html', {
                    'family': family, 'summary': summary, 'doctor': doctor
                })

        elif search_type == 'personal':
            patient = Patient.objects.filter(patient_id=query).first()
            if patient:
                log_doctor_access(doctor, 'PERSONAL', patient=patient)
                if request.GET.get('expand') == 'true' and patient.family:
                    log_doctor_access(doctor, 'EXPANDED', patient=patient, family=patient.family)
                    summary = get_family_disease_summary(patient.family)
                    return render(request, 'doctor/family_result.html', {
                        'family': patient.family, 'summary': summary, 'doctor': doctor
                    })
                return redirect('doctor_patient_detail', patient_id=patient.patient_id)

        if search_type == 'personal':
            messages.error(request, "Personal Health ID not found. Please verify the 4-character ID.")
        elif search_type == 'family':
            messages.error(request, "Family Health ID not found. Please verify the 6-digit code.")
        else:
            messages.error(request, "Invalid search type. Please select Personal ID or Family ID.")
        return redirect('doctor_search')

    return render(request, 'doctor/search.html', {'doctor': doctor})


def doctor_patient_detail_view(request, patient_id):
    doctor = get_session_doctor(request)
    if not doctor:
        request.session.flush()
        return redirect("doctor_login")

    patient = Patient.objects.filter(patient_id=patient_id).first()
    if not patient:
        messages.error(request, "Personal Health ID not found.")
        return redirect('doctor_search')

    log_doctor_access(doctor, 'PERSONAL', patient=patient)
    consultations = ConsultationRecord.objects.filter(patient=patient).order_by('-created_at')

    return render(request, 'doctor/patient_result.html', {
        'patient': patient,
        'doctor': doctor,
        'consultations': consultations,
    })


# ── AI Review ─────────────────────────────────────────────────────────────────

def review_prediction(request, symptom_id):
    doctor = get_session_doctor(request)
    if not doctor:
        return redirect('doctor_login')

    symptom = get_object_or_404(Symptom, id=symptom_id)

    # Authorization: must have accessed patient via Health ID or approved appointment
    has_access = DoctorAccessLog.objects.filter(doctor=doctor, patient=symptom.patient).exists()
    has_apt = Appointment.objects.filter(
        doctor=doctor, patient=symptom.patient, status__in=['APPROVED', 'COMPLETED']
    ).exists()
    if not (has_access or has_apt):
        messages.error(request, "You are not authorized to review this record.")
        return redirect('doctor_search')

    old_status = symptom.ai_prediction_status
    old_catalog_id = symptom.doctor_final_diagnosis_catalog_id

    if request.method == 'POST':
        form = AIReviewForm(request.POST, instance=symptom)
        if form.is_valid():
            sympt = form.save(commit=False)
            sympt.verified_by_doctor = doctor
            sympt.verified_at = timezone.now()
            sympt.save()

            new_catalog = sympt.doctor_final_diagnosis_catalog
            AIReviewLog.objects.create(
                symptom=sympt,
                doctor=doctor,
                previous_status=old_status,
                new_status=sympt.ai_prediction_status,
                previous_diagnosis_text=sympt.predicted_disease,
                new_diagnosis_text=(
                    new_catalog.name if new_catalog else sympt.doctor_modified_diagnosis_text
                ),
                previous_catalog_id=old_catalog_id,
                new_catalog_id=new_catalog.id if new_catalog else None,
                note=sympt.verification_note,
            )
            messages.success(request, "AI Prediction verified successfully.")
            return redirect('doctor_patient_detail', patient_id=symptom.patient.patient_id)
    else:
        form = AIReviewForm(instance=symptom)

    return render(request, 'doctor/review_prediction.html', {
        'form': form,
        'symptom': symptom,
        'doctor': doctor,
    })


# ── Appointments ──────────────────────────────────────────────────────────────

def doctor_appointments(request):
    doctor = get_session_doctor(request)
    if not doctor:
        return redirect("doctor_login")

    if request.method == "POST" and "reschedule_action" in request.POST:
        apt_id = request.POST.get("apt_id")
        action = request.POST.get("reschedule_action")
        apt = get_object_or_404(Appointment, id=apt_id, doctor=doctor)
        
        if not apt.hospital:
            if action == 'PROPOSE':
                apt.reschedule_requested_by = 'DOCTOR'
                apt.reschedule_date = request.POST.get('reschedule_date') or None
                apt.reschedule_time = request.POST.get('reschedule_time') or None
                apt.reschedule_reason = request.POST.get('reschedule_reason')
                apt.save()
                messages.success(request, "Reschedule proposal sent to patient.")
            elif action == 'ACCEPT' and apt.reschedule_requested_by == 'PATIENT':
                apt.preferred_date = apt.reschedule_date
                if apt.reschedule_time:
                    apt.appointment_time = apt.reschedule_time
                apt.reschedule_requested_by = None
                apt.reschedule_date = None
                apt.reschedule_time = None
                apt.reschedule_reason = None
                apt.save()
                messages.success(request, "Patient reschedule request accepted.")
            elif action == 'REJECT' and apt.reschedule_requested_by == 'PATIENT':
                apt.reschedule_requested_by = None
                apt.reschedule_date = None
                apt.reschedule_time = None
                apt.reschedule_reason = None
                apt.save()
                messages.success(request, "Patient reschedule request rejected.")
        return redirect('doctor_appointments')

    today = timezone.now().date()

    requested = Appointment.objects.filter(doctor=doctor, status='REQUESTED').order_by('preferred_date')
    upcoming = Appointment.objects.filter(
        doctor=doctor, status='APPROVED', preferred_date__gte=today
    ).order_by('preferred_date')
    past_completed = Appointment.objects.filter(
        doctor=doctor, status='COMPLETED'
    ).order_by('-preferred_date')
    cancelled = Appointment.objects.filter(
        doctor=doctor, status__in=['CANCELLED', 'REJECTED']
    ).order_by('-preferred_date')

    return render(request, "doctor/appointments.html", {
        "doctor": doctor,
        "requested": requested,
        "upcoming": upcoming,
        "past_completed": past_completed,
        "cancelled": cancelled,
    })


def update_appointment_status(request, apt_id, target_status):
    """POST-only. Valid transitions:
       REQUESTED → APPROVED, REJECTED
       APPROVED  → CANCELLED
       (COMPLETED only via save_consultation)
    """
    if request.method != "POST":
        return redirect('doctor_appointments')

    doctor = get_session_doctor(request)
    if not doctor:
        return redirect("doctor_login")

    apt = get_object_or_404(Appointment, id=apt_id, doctor=doctor)

    valid_transitions = {
        'REQUESTED': ['APPROVED', 'REJECTED'],
        'APPROVED': ['CANCELLED'],
    }

    if apt.status in valid_transitions and target_status in valid_transitions[apt.status]:
        apt.status = target_status
        if target_status == 'APPROVED':
            apt.approved_at = timezone.now()
            meeting_info = request.POST.get('meeting_link_or_address', '').strip()
            if meeting_info and not apt.hospital:
                apt.meeting_link_or_address = meeting_info
        elif target_status == 'REJECTED':
            apt.rejected_at = timezone.now()
            apt.rejection_reason = request.POST.get('rejection_reason', '').strip() or None
        elif target_status == 'CANCELLED':
            apt.cancelled_at = timezone.now()
            apt.cancellation_reason = request.POST.get('cancellation_reason', '').strip() or None
        apt.save()
        messages.success(request, f"Appointment {target_status.lower()} successfully.")
    else:
        messages.error(request, "Invalid status transition.")

    return redirect('doctor_appointments')


# ── My Patients ───────────────────────────────────────────────────────────────

def my_patients(request):
    doctor = get_session_doctor(request)
    if not doctor:
        return redirect("doctor_login")

    accessed_ids = DoctorAccessLog.objects.filter(doctor=doctor).values_list('patient_id', flat=True)
    apt_patient_ids = Appointment.objects.filter(
        doctor=doctor, status__in=['APPROVED', 'COMPLETED']
    ).values_list('patient_id', flat=True)

    patients = Patient.objects.filter(
        Q(id__in=accessed_ids) | Q(id__in=apt_patient_ids)
    ).distinct()

    query = request.GET.get('q', '').strip()
    if query:
        patients = patients.filter(
            Q(patient_id__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query)
        )

    return render(request, "doctor/my_patients.html", {"doctor": doctor, "patients": patients})


# ── Pending AI Reviews ────────────────────────────────────────────────────────

def pending_reviews(request):
    doctor = get_session_doctor(request)
    if not doctor:
        return redirect("doctor_login")

    accessed_ids = DoctorAccessLog.objects.filter(doctor=doctor).values_list('patient_id', flat=True)
    symptoms = Symptom.objects.filter(
        patient__id__in=accessed_ids, ai_prediction_status='PENDING_REVIEW'
    ).order_by('-created_at')

    return render(request, "doctor/pending_reviews.html", {"doctor": doctor, "symptoms": symptoms})


# ── Add Consultation ──────────────────────────────────────────────────────────

def add_consultation(request, patient_id):
    doctor = get_session_doctor(request)
    if not doctor:
        return redirect("doctor_login")

    patient = get_object_or_404(Patient, patient_id=patient_id)

    # Authorization: must have accessed patient or have an approved/completed appointment
    has_access = DoctorAccessLog.objects.filter(doctor=doctor, patient=patient).exists()
    has_apt = Appointment.objects.filter(
        doctor=doctor, patient=patient, status__in=['APPROVED', 'COMPLETED']
    ).exists()
    if not (has_access or has_apt):
        messages.error(request, "You are not authorized to consult this patient.")
        return redirect('doctor_search')

    # Build disease→is_hereditary map for JS warning
    diseases_json = {
        str(d.id): d.is_hereditary
        for d in DiseaseCatalog.objects.all()
    }

    # Pre-fill appointment from GET param
    preselected_apt_id = request.GET.get('appointment_id', '')

    if request.method == "POST":
        form = ConsultationForm(request.POST, request.FILES)
        if form.is_valid():
            consult = form.save(commit=False)
            consult.patient = patient
            consult.doctor = doctor

            apt_id = request.POST.get('appointment_id')
            if apt_id:
                apt = Appointment.objects.filter(
                    id=apt_id, doctor=doctor, patient=patient
                ).first()
                if apt and apt.status == 'APPROVED':
                    consult.appointment = apt
                    apt.status = 'COMPLETED'
                    apt.completed_at = timezone.now()
                    # Copy doctor instructions and follow_up_date from consultation to appointment
                    if consult.doctor_instructions:
                        apt.doctor_instructions = consult.doctor_instructions
                    if consult.follow_up_date:
                        apt.follow_up_date = consult.follow_up_date
                    apt.save()

            consult.save()

            # Create PatientDisease if a disease was selected
            disease = form.cleaned_data.get('disease_catalog')
            if disease:
                if not PatientDisease.objects.filter(
                    patient=patient, disease=disease, is_active=True
                ).exists():
                    PatientDisease.objects.create(
                        patient=patient,
                        disease=disease,
                        diagnosed_date=timezone.now().date(),
                        is_active=True,
                    )

            messages.success(request, "Consultation record saved successfully.")
            return redirect('doctor_patient_detail', patient_id=patient.patient_id)
    else:
        form = ConsultationForm()

    appointments = Appointment.objects.filter(
        doctor=doctor, patient=patient, status='APPROVED'
    )

    import json
    return render(request, "doctor/add_consultation.html", {
        "doctor": doctor,
        "patient": patient,
        "form": form,
        "appointments": appointments,
        "diseases_json": json.dumps(diseases_json),
        "preselected_apt_id": preselected_apt_id,
    })


# ── Hospital Affiliations (doctor-side) ───────────────────────────────────────

def hospital_affiliations(request):
    doctor = get_session_doctor(request)
    if not doctor:
        return redirect("doctor_login")

    if request.method == "POST":
        hosp_id = request.POST.get('hospital_id')
        hospital = get_object_or_404(Hospital, id=hosp_id)

        affil, created = HospitalAffiliation.objects.get_or_create(
            doctor=doctor, hospital=hospital
        )
        if not created and affil.status == 'REJECTED':
            affil.status = 'PENDING'
            affil.requested_at = timezone.now()
            affil.save()
            messages.success(request, f"Re-requested affiliation with {hospital.name}.")
        elif created:
            messages.success(request, f"Affiliation requested with {hospital.name}.")
        else:
            messages.info(request, f"Affiliation with {hospital.name} is already {affil.status}.")

        return redirect('doctor_hospital_affiliations')

    affiliations = HospitalAffiliation.objects.filter(doctor=doctor).select_related('hospital')
    linked_hosp_ids = affiliations.values_list('hospital_id', flat=True)
    available_hospitals = Hospital.objects.exclude(id__in=linked_hosp_ids)

    return render(request, "doctor/hospital_affiliations.html", {
        "doctor": doctor,
        "affiliations": affiliations,
        "available_hospitals": available_hospitals,
    })


# ── Disease Catalog Management ──────────────────────────────────────────────────

def doctor_disease_catalog(request):
    doctor = get_session_doctor(request)
    if not doctor:
        return redirect("doctor_login")
        
    from patient.models import DiseaseCatalog
    
    if request.method == "POST":
        disease_id = request.POST.get("disease_id")
        action = request.POST.get("action")
        
        disease = DiseaseCatalog.objects.filter(id=disease_id).first()
        if disease:
            if action == 'toggle_hereditary':
                disease.is_hereditary = not disease.is_hereditary
                disease.save()
                status = "hereditary" if disease.is_hereditary else "non-hereditary"
                messages.success(request, f"Marked {disease.name} as {status}.")
        return redirect('doctor_disease_catalog')
        
    diseases = DiseaseCatalog.objects.all().order_by('name')
    
    return render(request, "doctor/disease_catalog.html", {
        "doctor": doctor,
        "diseases": diseases,
    })