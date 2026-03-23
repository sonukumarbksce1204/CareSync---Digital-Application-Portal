from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .forms import HospitalForm
from .models import Hospital, HospitalImage
from django.contrib.auth.hashers import check_password


def get_session_hospital(request):
    hospital_id = request.session.get("hospital_id")
    if not hospital_id:
        return None
    return Hospital.objects.filter(id=hospital_id).first()


# ── Registration ──────────────────────────────────────────────────────────────

def hospital_register(request):
    if request.method == 'POST':
        form = HospitalForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('hospital_success')
    else:
        form = HospitalForm()
    return render(request, 'hospital/hospital_register.html', {'form': form})


def hospital_success(request):
    return render(request, 'hospital/hospital_success.html')


# ── Login / Logout ────────────────────────────────────────────────────────────

def hospital_login(request):
    if request.method == "POST":
        reg_no = request.POST.get("registration_number")
        password = request.POST.get("password")

        try:
            hospital = Hospital.objects.get(registration_number=reg_no)
            if check_password(password, hospital.password):
                request.session['hospital_id'] = hospital.id
                messages.success(request, f"Welcome {hospital.name}!")
                return redirect('hospital_dashboard')
            else:
                messages.error(request, "Invalid password.")
        except Hospital.DoesNotExist:
            messages.error(request, "Hospital with this registration number does not exist.")

    return render(request, "hospital/hospital_login.html")


def hospital_logout(request):
    request.session.flush()
    return redirect('hospital_login')


# ── Dashboard ─────────────────────────────────────────────────────────────────

def hospital_dashboard(request):
    hospital = get_session_hospital(request)
    if not hospital:
        request.session.flush()
        return redirect("hospital_login")

    if request.method == "POST" and request.FILES.get("image"):
        HospitalImage.objects.create(hospital=hospital, image=request.FILES["image"])
        return redirect("hospital_dashboard")

    images = hospital.images.all()

    # Real affiliated doctors (APPROVED only)
    from doctor.models import HospitalAffiliation
    affiliated_doctors = HospitalAffiliation.objects.filter(
        hospital=hospital, status='APPROVED'
    ).select_related('doctor').order_by('-responded_at')[:10]

    # Real upcoming appointments for this hospital
    from patient.models import Appointment
    recent_appointments = Appointment.objects.filter(
        hospital=hospital, status__in=['REQUESTED', 'APPROVED']
    ).select_related('patient__user').order_by('preferred_date', 'appointment_time')[:10]

    stats = {
        'total_beds': hospital.total_beds,
        'emergency': hospital.emergency_services,
        'established': hospital.established_year,
        'affiliated_doctors_count': HospitalAffiliation.objects.filter(hospital=hospital, status='APPROVED').count(),
        'pending_affiliations': HospitalAffiliation.objects.filter(hospital=hospital, status='PENDING').count(),
    }

    return render(request, "hospital/hospital_dashboard.html", {
        "hospital": hospital,
        "images": images,
        "affiliated_doctors": affiliated_doctors,
        "recent_appointments": recent_appointments,
        "stats": stats,
    })


# ── Patient Search ────────────────────────────────────────────────────────────

from patient.services.access_service import log_hospital_access
from patient.models import Patient, Family
from patient.services.family_service import get_family_disease_summary


def hospital_search_view(request):
    hospital = get_session_hospital(request)
    if not hospital:
        request.session.flush()
        return redirect("hospital_login")

    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type')

    if query:
        if search_type == 'family':
            family = Family.objects.filter(family_id=query).first()
            if family:
                log_hospital_access(hospital, 'FAMILY', family=family)
                summary = get_family_disease_summary(family)
                return render(request, 'hospital/family_result.html', {
                    'family': family, 'summary': summary, 'hospital': hospital
                })

        elif search_type == 'personal':
            patient = Patient.objects.filter(patient_id=query).first()
            if patient:
                log_hospital_access(hospital, 'PERSONAL', patient=patient)

                if request.GET.get('expand') == 'true' and patient.family:
                    log_hospital_access(hospital, 'EXPANDED', patient=patient, family=patient.family)
                    summary = get_family_disease_summary(patient.family)
                    return render(request, 'hospital/family_result.html', {
                        'family': patient.family, 'summary': summary, 'hospital': hospital
                    })

                return redirect('hospital_patient_detail', patient_id=patient.patient_id)

        if search_type == 'personal':
            messages.error(request, "Personal Health ID not found. Please verify the 4-character ID.")
        elif search_type == 'family':
            messages.error(request, "Family Health ID not found. Please verify the 6-digit code.")
        else:
            messages.error(request, "Invalid search type.")
        return redirect('hospital_search')

    return render(request, 'hospital/search.html', {'hospital': hospital})


def hospital_patient_detail_view(request, patient_id):
    hospital = get_session_hospital(request)
    if not hospital:
        request.session.flush()
        return redirect("hospital_login")

    patient = Patient.objects.filter(patient_id=patient_id).first()
    if not patient:
        messages.error(request, "Personal Health ID not found.")
        return redirect('hospital_search')

    log_hospital_access(hospital, 'PERSONAL', patient=patient)
    return render(request, 'hospital/patient_result.html', {
        'patient': patient, 'hospital': hospital
    })


# ── Doctor Affiliations ───────────────────────────────────────────────────────

from doctor.models import HospitalAffiliation


def hospital_affiliations(request):
    hospital = get_session_hospital(request)
    if not hospital:
        request.session.flush()
        return redirect("hospital_login")

    if request.method == "POST":
        action = request.POST.get('action')
        affil_id = request.POST.get('affiliation_id')
        affil = HospitalAffiliation.objects.filter(id=affil_id, hospital=hospital).first()

        if affil:
            if action == 'APPROVE':
                affil.status = 'APPROVED'
                messages.success(request, f"Approved affiliation for Dr. {affil.doctor.full_name}.")
            elif action == 'REJECT':
                affil.status = 'REJECTED'
                messages.success(request, f"Rejected affiliation for Dr. {affil.doctor.full_name}.")
            affil.responded_at = timezone.now()
            affil.save()

    pending_requests = HospitalAffiliation.objects.filter(
        hospital=hospital, status='PENDING'
    ).select_related('doctor')
    resolved_requests = HospitalAffiliation.objects.filter(
        hospital=hospital
    ).exclude(status='PENDING').select_related('doctor').order_by('-responded_at')

    return render(request, "hospital/affiliations.html", {
        "hospital": hospital,
        "pending_requests": pending_requests,
        "resolved_requests": resolved_requests,
    })


# ── Hospital Appointments ─────────────────────────────────────────────────────

def hospital_appointments(request):
    hospital = get_session_hospital(request)
    if not hospital:
        request.session.flush()
        return redirect("hospital_login")
        
    if request.method == "POST":
        action = request.POST.get('action')
        apt_id = request.POST.get('appointment_id')
        doctor_id = request.POST.get('doctor_id')
        
        from patient.models import Appointment
        from doctor.models import Doctor, HospitalAffiliation
        
        apt = Appointment.objects.filter(id=apt_id, hospital=hospital).first()
        if apt:
            if action == 'APPROVE' and doctor_id:
                doctor = Doctor.objects.filter(doctor_id=doctor_id).first()
                # Verify doctor is affiliated and approved
                is_affiliated = HospitalAffiliation.objects.filter(
                    hospital=hospital, doctor=doctor, status='APPROVED'
                ).exists()
                
                if doctor and is_affiliated:
                    apt.doctor = doctor
                    apt.status = 'APPROVED'
                    apt.approved_at = timezone.now()
                    apt.save()
                    messages.success(request, f"Appointment allocated to Dr. {doctor.full_name}.")
                else:
                    messages.error(request, "Selected doctor is not an approved affiliate.")
            elif action == 'REJECT':
                apt.status = 'REJECTED'
                apt.rejected_at = timezone.now()
                apt.rejection_reason = "Rejected by hospital administration."
                apt.save()
                messages.success(request, "Appointment request rejected.")
            elif action == 'RESCHEDULE_PROPOSE':
                apt.reschedule_requested_by = 'HOSPITAL'
                apt.reschedule_date = request.POST.get('reschedule_date') or None
                apt.reschedule_time = request.POST.get('reschedule_time') or None
                apt.reschedule_reason = request.POST.get('reschedule_reason')
                apt.save()
                messages.success(request, "Reschedule proposal sent to patient.")
            elif action == 'RESCHEDULE_ACCEPT' and apt.reschedule_requested_by == 'PATIENT':
                apt.preferred_date = apt.reschedule_date
                if apt.reschedule_time:
                    apt.appointment_time = apt.reschedule_time
                apt.reschedule_requested_by = None
                apt.reschedule_date = None
                apt.reschedule_time = None
                apt.reschedule_reason = None
                apt.save()
                messages.success(request, "Patient reschedule request accepted.")
            elif action == 'RESCHEDULE_REJECT' and apt.reschedule_requested_by == 'PATIENT':
                apt.reschedule_requested_by = None
                apt.reschedule_date = None
                apt.reschedule_time = None
                apt.reschedule_reason = None
                apt.save()
                messages.success(request, "Patient reschedule request rejected.")
            
        return redirect('hospital_appointments')
        
    from patient.models import Appointment
    from doctor.models import HospitalAffiliation
    
    requested = Appointment.objects.filter(
        hospital=hospital, status='REQUESTED'
    ).select_related('patient__user').order_by('preferred_date')
    
    approved = Appointment.objects.filter(
        hospital=hospital, status='APPROVED'
    ).select_related('patient__user', 'doctor').order_by('preferred_date')
    
    completed = Appointment.objects.filter(
        hospital=hospital, status='COMPLETED'
    ).select_related('patient__user', 'doctor').order_by('-preferred_date')
    
    cancelled = Appointment.objects.filter(
        hospital=hospital, status__in=['CANCELLED', 'REJECTED']
    ).select_related('patient__user', 'doctor').order_by('-preferred_date')
    
    affiliated_doctors = HospitalAffiliation.objects.filter(
        hospital=hospital, status='APPROVED'
    ).select_related('doctor')
    
    return render(request, "hospital/appointments.html", {
        "hospital": hospital,
        "requested": requested,
        "approved": approved,
        "completed": completed,
        "cancelled": cancelled,
        "affiliated_doctors": affiliated_doctors,
    })