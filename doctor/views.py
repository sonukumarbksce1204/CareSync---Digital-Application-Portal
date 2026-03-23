from django.shortcuts import render, redirect
from .models import Doctor, Specialization, DoctorVerification, Qualification
from django.contrib import messages

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

        # password match check
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return render(request, "doctor/signup.html", {"specializations": specializations})

        # email exists check
        if Doctor.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return render(request, "doctor/signup.html", {"specializations": specializations})

        # phone exists check
        if Doctor.objects.filter(phone=phone).exists():
            messages.error(request, "Phone number already registered")
            return render(request, "doctor/signup.html", {"specializations": specializations})

        # license number exists check
        if DoctorVerification.objects.filter(license_number=license_number).exists():
            messages.error(request, "License number already registered")
            return render(request, "doctor/signup.html", {"specializations": specializations})

        # create doctor
        doctor = Doctor(
            full_name=full_name,
            email=email,
            phone=phone,
            experience_years=experience,
        )

        doctor.set_password(password)
        doctor.save()

        # assign many specializations
        doctor.specializations.set(selected_specs)

        # create verification
        DoctorVerification.objects.create(
            doctor=doctor,
            license_number=license_number,
            license_document=license_file
        )

        # create qualification (simple initial)
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



from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Doctor


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


def get_session_doctor(request):
    doctor_id = request.session.get("doctor_id")
    if not doctor_id: return None
    return Doctor.objects.filter(doctor_id=doctor_id).first()

from patient.models import Appointment
from .models import HospitalAffiliation
from django.db.models import Q
from django.utils import timezone
from .forms import DoctorProfileUpdateForm, ConsultationForm

def doctor_dashboard(request):
    doctor = get_session_doctor(request)
    if not doctor:
        request.session.flush()
        return redirect("doctor_login")

    pending_appointments = Appointment.objects.filter(doctor=doctor, status='REQUESTED').count()
    upcoming_appointments = Appointment.objects.filter(doctor=doctor, status='APPROVED', preferred_date__gte=timezone.now().date()).count()
    
    from patient.models import DoctorAccessLog, Patient, Symptom
    accessed_patient_ids = DoctorAccessLog.objects.filter(doctor=doctor).values_list('patient_id', flat=True)
    apt_patient_ids = Appointment.objects.filter(doctor=doctor, status__in=['APPROVED', 'COMPLETED']).values_list('patient_id', flat=True)
    my_patients_count = Patient.objects.filter(Q(id__in=accessed_patient_ids) | Q(id__in=apt_patient_ids)).distinct().count()
    
    pending_reviews_count = Symptom.objects.filter(patient__id__in=accessed_patient_ids, ai_prediction_status='PENDING_REVIEW').count()

    return render(request, "doctor/dashboard.html", {
        "doctor": doctor,
        "pending_appointments": pending_appointments,
        "upcoming_appointments": upcoming_appointments,
        "my_patients_count": my_patients_count,
        "pending_reviews_count": pending_reviews_count
    })


def doctor_logout(request):
    request.session.flush()
    return redirect("doctor_login")


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

    qualifications = doctor.qualifications.all()
    specializations = doctor.specializations.all()
    affiliations = doctor.affiliations.filter(status='APPROVED')

    return render(request, "doctor/profile.html", {
        "doctor": doctor,
        "form": form,
        "qualifications": qualifications,
        "specializations": specializations,
        "affiliations": affiliations
    })


from patient.services.access_service import log_doctor_access
from patient.models import Patient, Family
from patient.services.family_service import get_family_disease_summary

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
                return render(request, 'doctor/family_result.html', {'family': family, 'summary': summary, 'doctor': doctor})
                
        elif search_type == 'personal':
            patient = Patient.objects.filter(patient_id=query).first()
            if patient:
                log_doctor_access(doctor, 'PERSONAL', patient=patient)
                
                if request.GET.get('expand') == 'true' and patient.family:
                    log_doctor_access(doctor, 'EXPANDED', patient=patient, family=patient.family)
                    summary = get_family_disease_summary(patient.family)
                    return render(request, 'doctor/family_result.html', {'family': patient.family, 'summary': summary, 'doctor': doctor})
                
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
    
    # Fetch consultations for the view
    from patient.models import ConsultationRecord
    consultations = ConsultationRecord.objects.filter(patient=patient).order_by('-created_at')
    
    return render(request, 'doctor/patient_result.html', {'patient': patient, 'doctor': doctor, 'consultations': consultations})

from patient.models import Symptom, DoctorAccessLog, AIReviewLog
from .forms import AIReviewForm
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

def review_prediction(request, symptom_id):
    doctor = get_session_doctor(request)
    if not doctor: return redirect('doctor_login')
    
    symptom = get_object_or_404(Symptom, id=symptom_id)
    
    # AUTHORIZATION CHECK: Must have accessed patient via Health ID
    has_access = DoctorAccessLog.objects.filter(doctor=doctor, patient=symptom.patient).exists()
    if not has_access:
        messages.error(request, "You are not authorized to review this record. You must connect with the patient via Health ID first.")
        return redirect('doctor_search')

    old_status = symptom.ai_prediction_status

    if request.method == 'POST':
        form = AIReviewForm(request.POST, instance=symptom)
        if form.is_valid():
            sympt = form.save(commit=False)
            sympt.verified_by_doctor = doctor
            sympt.verified_at = timezone.now()
            sympt.save()
            
            # Log action
            AIReviewLog.objects.create(
                symptom=sympt,
                doctor=doctor,
                previous_status=old_status,
                new_status=sympt.ai_prediction_status,
                previous_diagnosis_text=sympt.predicted_disease,
                new_diagnosis_text=sympt.doctor_modified_diagnosis_text if sympt.ai_prediction_status == 'MODIFIED' else sympt.doctor_diagnosis_notes,
                new_catalog_id=None,
                note=sympt.verification_note
            )
            messages.success(request, "AI Prediction verified successfully.")
            return redirect('doctor_patient_detail', patient_id=symptom.patient.patient_id)
    else:
        form = AIReviewForm(instance=symptom)

    return render(request, 'doctor/review_prediction.html', {'form': form, 'symptom': symptom, 'doctor': doctor})


# --- APPOINTMENTS MANAGEMENT ---
def doctor_appointments(request):
    doctor = get_session_doctor(request)
    if not doctor: return redirect("doctor_login")

    today = timezone.now().date()
    
    requested = Appointment.objects.filter(doctor=doctor, status='REQUESTED').order_by('preferred_date')
    upcoming = Appointment.objects.filter(doctor=doctor, status='APPROVED', preferred_date__gte=today).order_by('preferred_date')
    past_completed = Appointment.objects.filter(
        Q(doctor=doctor) & 
        (Q(status='COMPLETED') | Q(status='APPROVED', preferred_date__lt=today))
    ).order_by('-preferred_date')
    cancelled = Appointment.objects.filter(doctor=doctor, status__in=['CANCELLED', 'REJECTED']).order_by('-preferred_date')

    return render(request, "doctor/appointments.html", {
        "doctor": doctor,
        "requested": requested,
        "upcoming": upcoming,
        "past_completed": past_completed,
        "cancelled": cancelled
    })

def update_appointment_status(request, apt_id, target_status):
    if request.method != "POST":
        return redirect('doctor_appointments')
        
    doctor = get_session_doctor(request)
    if not doctor: return redirect("doctor_login")

    apt = get_object_or_404(Appointment, id=apt_id, doctor=doctor)

    valid_transitions = {
        'REQUESTED': ['APPROVED', 'REJECTED', 'COMPLETED'],
        'APPROVED': ['IN_CONSULTATION', 'COMPLETED', 'CANCELLED'],
        'IN_CONSULTATION': ['COMPLETED', 'CANCELLED']
    }

    if apt.status in valid_transitions and target_status in valid_transitions[apt.status]:
        apt.status = target_status
        if target_status == 'APPROVED':
            apt.approved_at = timezone.now()
        elif target_status == 'COMPLETED':
            apt.completed_at = timezone.now()
        elif target_status == 'REJECTED':
            apt.rejected_at = timezone.now()
        elif target_status == 'CANCELLED':
            apt.cancelled_at = timezone.now()
        apt.save()
        messages.success(request, f"Appointment status updated to {target_status}.")
    else:
        messages.error(request, "Invalid status transition.")
        
    return redirect('doctor_appointments')


# --- MY PATIENTS ---
def my_patients(request):
    doctor = get_session_doctor(request)
    if not doctor: return redirect("doctor_login")

    from patient.models import DoctorAccessLog, Patient

    accessed_ids = DoctorAccessLog.objects.filter(doctor=doctor).values_list('patient_id', flat=True)
    apt_patient_ids = Appointment.objects.filter(doctor=doctor, status__in=['APPROVED', 'COMPLETED']).values_list('patient_id', flat=True)
    
    patients = Patient.objects.filter(Q(id__in=accessed_ids) | Q(id__in=apt_patient_ids)).distinct()
    
    query = request.GET.get('q', '').strip()
    if query:
        patients = patients.filter(Q(patient_id__icontains=query) | Q(user__first_name__icontains=query) | Q(user__last_name__icontains=query))

    return render(request, "doctor/my_patients.html", {"doctor": doctor, "patients": patients})


# --- PENDING REVIEWS ---
def pending_reviews(request):
    doctor = get_session_doctor(request)
    if not doctor: return redirect("doctor_login")
    
    from patient.models import DoctorAccessLog, Symptom

    accessed_ids = DoctorAccessLog.objects.filter(doctor=doctor).values_list('patient_id', flat=True)
    symptoms = Symptom.objects.filter(patient__id__in=accessed_ids, ai_prediction_status='PENDING_REVIEW').order_by('-created_at')

    return render(request, "doctor/pending_reviews.html", {"doctor": doctor, "symptoms": symptoms})


# --- ADD CONSULTATION ---
from patient.models import PatientDisease

def add_consultation(request, patient_id):
    doctor = get_session_doctor(request)
    if not doctor: return redirect("doctor_login")

    from patient.models import Patient
    patient = get_object_or_404(Patient, patient_id=patient_id)
    
    # Check "My Patients" authorization
    from patient.models import DoctorAccessLog
    has_access = DoctorAccessLog.objects.filter(doctor=doctor, patient=patient).exists()
    has_apt = Appointment.objects.filter(doctor=doctor, patient=patient, status__in=['APPROVED', 'COMPLETED']).exists()
    if not (has_access or has_apt):
        messages.error(request, "You are not authorized to consult this patient unless they are in your 'My Patients' list.")
        return redirect('doctor_search')

    if request.method == "POST":
        form = ConsultationForm(request.POST, request.FILES)
        if form.is_valid():
            consult = form.save(commit=False)
            consult.patient = patient
            consult.doctor = doctor
            
            apt_id = request.POST.get('appointment_id')
            if apt_id:
                apt = Appointment.objects.filter(id=apt_id, doctor=doctor, patient=patient).first()
                if apt:
                    consult.appointment = apt
                    if apt.status != 'COMPLETED':
                        apt.status = 'COMPLETED'
                        apt.completed_at = timezone.now()
                        apt.save()
            
            consult.save()
            
            disease = form.cleaned_data.get('disease_catalog')
            if disease:
                if not PatientDisease.objects.filter(patient=patient, disease=disease, is_active=True).exists():
                    PatientDisease.objects.create(patient=patient, disease=disease, diagnosed_date=timezone.now().date(), is_active=True)

            messages.success(request, "Consultation record and diagnosis saved successfully.")
            return redirect('doctor_patient_detail', patient_id=patient.patient_id)
    else:
        form = ConsultationForm()
        
    appointments = Appointment.objects.filter(doctor=doctor, patient=patient, status__in=['REQUESTED', 'APPROVED'])

    return render(request, "doctor/add_consultation.html", {"doctor": doctor, "patient": patient, "form": form, "appointments": appointments})


# --- HOSPITAL AFFILIATIONS ---
from hospital.models import Hospital

def hospital_affiliations(request):
    doctor = get_session_doctor(request)
    if not doctor: return redirect("doctor_login")

    if request.method == "POST":
        hosp_id = request.POST.get('hospital_id')
        hospital = get_object_or_404(Hospital, id=hosp_id)
        
        affil, created = HospitalAffiliation.objects.get_or_create(doctor=doctor, hospital=hospital)
        if not created and affil.status == 'REJECTED':
            affil.status = 'PENDING'
            affil.requested_at = timezone.now()
            affil.save()
            messages.success(request, f"Re-requested affiliation with {hospital.name}.")
        elif created:
            messages.success(request, f"Requested affiliation with {hospital.name}.")
        else:
            messages.info(request, f"Affiliation request with {hospital.name} is already {affil.status}.")
            
        return redirect('hospital_affiliations')

    affiliations = HospitalAffiliation.objects.filter(doctor=doctor)
    linked_hosp_ids = affiliations.values_list('hospital_id', flat=True)
    available_hospitals = Hospital.objects.exclude(id__in=linked_hosp_ids)

    return render(request, "doctor/hospital_affiliations.html", {
        "doctor": doctor,
        "affiliations": affiliations,
        "available_hospitals": available_hospitals
    })