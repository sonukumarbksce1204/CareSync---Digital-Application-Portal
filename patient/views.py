from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from .forms import PatientSignUpForm, PatientProfileForm, SymptomForm, AppointmentForm, PatientProfileUpdateForm
from .models import Patient, Family, Symptom, Appointment
from hospital.models import Hospital
from doctor.models import Doctor


# ── ML setup (SAFE & ORDER-PRESERVING) ─────────────────────────────────────
_ML_CACHE = {}


def _load_ml():
    """
    Load symptom list ALWAYS.
    Load ML model ONLY if predictor.is_ready() is True.
    NEVER blocks UI or saving.
    """
    if _ML_CACHE:
        return _ML_CACHE

    result = {
        'predict_text':     None,
        'predict_selected': None,
        'predict_top_text': None,
        'symptom_list':     [],
        'ml_available':     False,
    }

    # ── 1. Load symptom list (NO TensorFlow needed) ──
    try:
        import os, joblib
        _here = os.path.dirname(os.path.abspath(__file__))
        _pkl  = os.path.join(_here, '..', 'ml_model', 'symptom_index.pkl')
        idx   = joblib.load(_pkl)

        # IMPORTANT: preserve exact training order
        result['symptom_list'] = list(idx.keys())
    except Exception as e:
        print("❌ Symptom index load failed:", e)

    # ── 2. Load ML predictor (NO RELOAD, uses module cache) ──
    try:
        from ml_model import predictor  # NO importlib.reload() - KEEPS MODEL CACHED

        if predictor.is_ready():   # Uses module-level _READY=True
            result['predict_text']     = predictor.predict_from_text
            result['predict_selected'] = predictor.predict_from_selected
            result['predict_top_text'] = predictor.get_top_predictions
            result['ml_available']     = True
            print("✅ Django sees ML model as READY")
        else:
            print("⚠ Django imported predictor but model not ready")

    except Exception as e:
        print("⚠ Django failed to import predictor:", e)

    _ML_CACHE.update(result)
    return _ML_CACHE


# ==============================
# PATIENT SIGNUP
# ==============================
def patient_signup(request):
    if request.method == "POST":
        user_form = PatientSignUpForm(request.POST)
        profile_form = PatientProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            login(request, user)
            return redirect("patient_dashboard")

    else:
        user_form = PatientSignUpForm()
        profile_form = PatientProfileForm()

    return render(request, "patient/patient_signup.html", {
        "user_form": user_form,
        "profile_form": profile_form,
    })


# ==============================
# PATIENT LOGIN
# ==============================
def patient_login(request):
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password"),
        )
        if user:
            login(request, user)
            return redirect("patient_dashboard")
        return render(request, "patient/patient_login.html", {
            "error": "Invalid credentials"
        })

    return render(request, "patient/patient_login.html")


# ==============================
# PATIENT DASHBOARD
# ==============================
def patient_dashboard(request):
    if not request.user.is_authenticated:
        return redirect("patient_login")

    patient = Patient.objects.filter(user=request.user).first()
    if not patient:
        return redirect("patient_signup")

    hospitals = Hospital.objects.all()[:6]
    message = prediction = None

    if request.method == "POST":

        # ── Family logic ─────────────────────────
        if "generate_family" in request.POST:
            if not patient.family:
                from .services.family_service import create_family_for_patient
                create_family_for_patient(patient)
                message = "New Family created successfully."
            else:
                message = "You are already connected to a family."

        # ── Add symptom + ML ─────────────────────
        elif "add_symptom" in request.POST:
            form = SymptomForm(request.POST, request.FILES)
            if form.is_valid():
                symptom = form.save(commit=False)
                symptom.patient = patient
                symptom.save()

                ml = _load_ml()
                selected = request.POST.getlist("selected_symptoms")

                # DEBUG PRINTS
                print("\n🔍 RAW INPUT:", selected)
                print("🔍 ML READY:", ml["ml_available"])
                print("🔍 FIRST 10 SYMPTOMS:", _load_ml()["symptom_list"][:10])
                print("🔍 SYMPTOM COUNT:", len(_load_ml()["symptom_list"]))

                if selected and ml["predict_selected"]:
                    res = ml["predict_selected"](selected, top_n=1)
                    print("🔍 PREDICTION RESULT:", res)
                    if res:
                        top = res["top"][0]
                        symptom.predicted_disease = top["disease"]
                        symptom.prediction_confidence = top["confidence"]
                        symptom.save(update_fields=[
                            "predicted_disease",
                            "prediction_confidence",
                        ])
                        prediction = top
                    else:
                        print("🔍 NO PREDICTION - symptoms not matched")
                else:
                    print("🔍 NO ML CALL - selected empty or ml not available")

                message = "Medical record added successfully."

    # ── Access control ─────────────────────────
    if patient.family and patient.family.head == patient:
        symptoms = Symptom.objects.filter(
            patient__family=patient.family, is_archived=False
        ).order_by("-created_at")
    else:
        symptoms = Symptom.objects.filter(
            patient=patient, is_archived=False
        ).order_by("-created_at")

    # ── Timeline Data Fetch ────────────────────────
    # Fetch consultation records and active diseases to pass to dashboard
    consultations = patient.consultations.filter(visible_to_patient=True).order_by('-created_at')
    diagnosed_diseases = patient.diseases.all().order_by('-diagnosed_date')

    return render(request, "patient/patient_dashboard.html", {
        "patient": patient,
        "hospitals": hospitals,
        "symptoms": symptoms,
        "consultations": consultations,
        "diagnosed_diseases": diagnosed_diseases,
        "symptom_form": SymptomForm(),
        "message": message,
        "prediction": prediction,
        "symptom_list": _load_ml()["symptom_list"],
    })


# ==============================
# PATIENT LOGOUT
# ==============================
def patient_logout(request):
    logout(request)
    return redirect("patient_login")


# ==============================
# DISEASE PREDICTOR
# ==============================
def disease_predictor(request):
    if not request.user.is_authenticated:
        return redirect("patient_login")

    patient = Patient.objects.filter(user=request.user).first()
    ml = _load_ml()

    result = error = None
    saved = False

    if request.method == "POST":
        selected = request.POST.getlist("symptoms")

        if not selected:
            error = "Please select at least one symptom."
        elif not ml["ml_available"]:
            error = "Prediction model not available on server."
        else:
            res = ml["predict_selected"](selected, top_n=3)
            if res:
                result = res
                top = res["top"][0]
                Symptom.objects.create(
                    patient=patient,
                    description=", ".join(selected),
                    address=patient.address or "Not specified",
                    predicted_disease=top["disease"],
                    prediction_confidence=top["confidence"],
                )
                saved = True
            else:
                error = "Symptoms not recognized."

    return render(request, "patient/disease_predict.html", {
        "patient": patient,
        "symptom_list": ml["symptom_list"],
        "result": result,
        "error": error,
        "saved": saved,
    })


# ==============================
# SYMPTOM SUGGESTIONS (AJAX)
# ==============================
def symptom_suggestions(request):
    if not request.user.is_authenticated:
        return JsonResponse([], safe=False)

    q = request.GET.get("q", "").lower()
    if not q:
        return JsonResponse([], safe=False)

    symptoms = _load_ml()["symptom_list"]
    return JsonResponse(
        [s for s in symptoms if q in s.replace("_", " ").lower()][:15],
        safe=False,
    )


# ==============================
# HEALTH ID: FAMILY HUB
# ==============================
from .services.family_service import change_family_head, get_family_disease_summary
from .forms import ChangeFamilyHeadForm

def family_hub_view(request):
    if not request.user.is_authenticated:
        return redirect("patient_login")
        
    patient = Patient.objects.filter(user=request.user).first()
    if not patient or not patient.family:
        return redirect('patient_dashboard')
        
    family = patient.family
    is_head = (family.head == patient)
    members = family.members.all()
    summary = get_family_disease_summary(family)
    
    from .models import FamilyJoinRequest
    pending_requests = FamilyJoinRequest.objects.filter(family=family, status='PENDING') if is_head else []
    
    return render(request, 'patient/family_hub.html', {
        'family': family, 'is_head': is_head, 'members': members, 'summary': summary, 'patient': patient, 'pending_requests': pending_requests
    })

def change_head_view(request):
    if not request.user.is_authenticated:
        return redirect("patient_login")
        
    patient = Patient.objects.filter(user=request.user).first()
    if not patient or not patient.family:
        return redirect('patient_dashboard')
        
    family = patient.family
    if family.head != patient:
        return redirect('patient_family_hub')

    form = ChangeFamilyHeadForm(request.POST or None, family=family)
    if request.method == 'POST' and form.is_valid():
        try:
            change_family_head(family, form.cleaned_data['new_head'], request.user, form.cleaned_data['reason'])
            return redirect('patient_family_hub')
        except ValueError as e:
            return render(request, 'patient/change_head.html', {'form': form, 'error': str(e), 'patient': patient})
        
    return render(request, 'patient/change_head.html', {'form': form, 'patient': patient})


from .models import FamilyJoinRequest
from .services.access_service import can_view_patient, can_manage_family
from .services.family_service import process_join_request, create_family_for_patient
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404


from django.contrib import messages
from .forms import RequestJoinFamilyForm

def request_join_family(request):
    if not request.user.is_authenticated: return redirect("patient_login")
    if request.method == "POST":
        patient = getattr(request.user, 'patient', None)
        form = RequestJoinFamilyForm(request.POST)
        if form.is_valid() and patient and not patient.family:
            family_id = form.cleaned_data['family_id']
            family = Family.objects.filter(family_id=family_id).first()
            if family:
                obj, created = FamilyJoinRequest.objects.get_or_create(
                    patient=patient, family=family, status='PENDING',
                    defaults={
                        'requested_relationship': form.cleaned_data['relationship'],
                        'custom_relationship': form.cleaned_data.get('custom_relationship', '')
                    }
                )
                if created:
                    messages.success(request, f"Request sent to Family {family.family_id}.")
                else:
                    messages.warning(request, "You already have a pending request for this family.")
        else:
            for error in form.errors.values():
                messages.error(request, error[0])
            if not form.errors:
                messages.error(request, "Invalid submission or already in a family.")
    return redirect('patient_dashboard')

def review_join_request(request, req_id, action):
    if request.method != 'POST':
        return HttpResponseForbidden("Method not allowed.")
    if not request.user.is_authenticated: return redirect("patient_login")
    join_req = get_object_or_404(FamilyJoinRequest, id=req_id)
    if not can_manage_family(request.user, join_req.family): 
        messages.error(request, "You are not the Head of this Family.")
        return redirect('patient_family_hub')
    
    if action in ['APPROVE', 'REJECT']:
        try:
            process_join_request(join_req, getattr(request.user, 'patient', None), action)
            messages.success(request, f"Request {action.lower()} successfully.")
        except Exception as e:
            messages.error(request, str(e))
    return redirect('patient_family_hub')

def member_history_view(request, member_id):
    if not request.user.is_authenticated: return redirect("patient_login")
    target = get_object_or_404(Patient, id=member_id)
    
    if not can_view_patient(request.user, target):
        return HttpResponseForbidden("You do not have permission to view this medical record. Only the Family Head can view this.")
        
    symptoms = target.symptoms.filter(is_archived=False).order_by('-created_at')
    consultations = target.consultations.order_by('-created_at')
    return render(request, 'patient/member_history.html', {'member': target, 'symptoms': symptoms, 'consultations': consultations})

# ==============================
# PATIENT PROFILE & INFO
# ==============================
def patient_profile(request):
    import django.contrib.messages as messages
    patient = Patient.objects.filter(user=request.user).first()
    if request.method == 'POST':
        form = PatientProfileUpdateForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('patient_profile')
    else:
        form = PatientProfileUpdateForm(instance=patient)
    return render(request, 'patient/profile.html', {'patient': patient, 'form': form})

def privacy_policy(request):
    return render(request, 'patient/privacy_policy.html', {'patient': Patient.objects.filter(user=request.user).first()})

def contact_page(request):
    return render(request, 'patient/contact.html', {'patient': Patient.objects.filter(user=request.user).first()})

# ==============================
# DISCOVERY (HOSPITALS & DOCTORS)
# ==============================
def hospitals_list(request):
    hospitals = Hospital.objects.all()
    q = request.GET.get('q')
    if q: hospitals = hospitals.filter(name__icontains=q)
    return render(request, 'patient/hospitals.html', {'hospitals': hospitals, 'patient': Patient.objects.filter(user=request.user).first()})

def hospital_detail(request, hospital_id):
    hospital = get_object_or_404(Hospital, id=hospital_id)
    return render(request, 'patient/hospital_detail.html', {'hospital': hospital, 'patient': Patient.objects.filter(user=request.user).first()})

def doctors_list(request):
    doctors = Doctor.objects.filter(verification_status='verified')
    return render(request, 'patient/doctors.html', {'doctors': doctors, 'patient': Patient.objects.filter(user=request.user).first()})

def doctor_detail(request, doc_id):
    doctor = get_object_or_404(Doctor, doctor_id=doc_id)
    return render(request, 'patient/doctor_detail.html', {'doctor': doctor, 'patient': Patient.objects.filter(user=request.user).first()})

# ==============================
# APPOINTMENTS
# ==============================
def appointments_view(request):
    patient = Patient.objects.filter(user=request.user).first()
    
    if request.method == "POST" and "reschedule_action" in request.POST:
        import django.contrib.messages as messages
        apt_id = request.POST.get("apt_id")
        action = request.POST.get("reschedule_action")
        apt = get_object_or_404(Appointment, id=apt_id, patient=patient)
        
        if action == 'REQUEST':
            apt.reschedule_requested_by = 'PATIENT'
            apt.reschedule_date = request.POST.get('reschedule_date') or None
            apt.reschedule_time = request.POST.get('reschedule_time') or None
            apt.reschedule_reason = request.POST.get('reschedule_reason')
            apt.save()
            messages.success(request, "Reschedule request sent to clinic/doctor.")
        elif action == 'ACCEPT' and apt.reschedule_requested_by in ['DOCTOR', 'HOSPITAL']:
            apt.preferred_date = apt.reschedule_date
            if apt.reschedule_time:
                apt.appointment_time = apt.reschedule_time
            apt.reschedule_requested_by = None
            apt.reschedule_date = None
            apt.reschedule_time = None
            apt.reschedule_reason = None
            apt.save()
            messages.success(request, "Reschedule proposal accepted.")
        elif action == 'REJECT' and apt.reschedule_requested_by in ['DOCTOR', 'HOSPITAL']:
            apt.reschedule_requested_by = None
            apt.reschedule_date = None
            apt.reschedule_time = None
            apt.reschedule_reason = None
            apt.save()
            messages.success(request, "Reschedule proposal rejected.")
        return redirect('patient_appointments')

    apps = patient.appointments.all().order_by('-created_at')
    
    upcoming = apps.filter(status__in=['REQUESTED', 'APPROVED', 'IN_CONSULTATION'])
    past = apps.filter(status='COMPLETED')
    cancelled = apps.filter(status__in=['CANCELLED', 'REJECTED'])
    
    return render(request, 'patient/appointments.html', {
        'patient': patient, 'upcoming': upcoming, 'past': past, 'cancelled': cancelled
    })

def book_appointment(request):
    import django.contrib.messages as messages
    patient = Patient.objects.filter(user=request.user).first()
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            dup = Appointment.objects.filter(
                patient=patient, preferred_date=form.cleaned_data['preferred_date'], 
                appointment_time=form.cleaned_data['appointment_time'],
                doctor=form.cleaned_data['doctor'], hospital=form.cleaned_data['hospital'],
                status__in=['REQUESTED', 'APPROVED', 'IN_CONSULTATION']
            ).exists()
            if dup:
                messages.error(request, 'You already have an active appointment request for this date/target.')
            else:
                apt = form.save(commit=False)
                apt.patient = patient
                apt.save()
                messages.success(request, 'Appointment requested successfully.')
                return redirect('patient_appointments')
    else:
        doc_id = request.GET.get('doctor')
        hosp_id = request.GET.get('hospital')
        form = AppointmentForm(initial={'doctor': doc_id, 'hospital': hosp_id})
    return render(request, 'patient/book_appointment.html', {'form': form, 'patient': patient})

def cancel_appointment(request, apt_id):
    import django.contrib.messages as messages
    from django.utils import timezone as tz
    if request.method != 'POST':
        return redirect('patient_appointments')
    patient = Patient.objects.filter(user=request.user).first()
    apt = get_object_or_404(Appointment, id=apt_id, patient=patient)
    if apt.status in ['REQUESTED', 'APPROVED']:
        apt.status = 'CANCELLED'
        apt.cancelled_at = tz.now()
        apt.cancellation_reason = request.POST.get('cancellation_reason', '').strip() or None
        apt.save()
        messages.success(request, 'Appointment cancelled.')
    else:
        messages.error(request, 'Cannot cancel this appointment.')
    return redirect('patient_appointments')


# ==============================
# MEDICAL HISTORY TIMELINE
# ==============================
def medical_history_view(request):
    if not request.user.is_authenticated:
        return redirect('patient_login')
    from .models import ConsultationRecord, PatientDisease
    patient = Patient.objects.filter(user=request.user).first()
    if not patient:
        return redirect('patient_signup')

    symptoms = patient.symptoms.filter(is_archived=False).order_by('-created_at')
    consultations = patient.consultations.filter(visible_to_patient=True).order_by('-created_at')
    diseases = patient.diseases.select_related('disease').order_by('-diagnosed_date')

    return render(request, 'patient/medical_history.html', {
        'patient': patient,
        'symptoms': symptoms,
        'consultations': consultations,
        'diseases': diseases,
    })

# ==============================
# MEDICAL HISTORY
# ==============================
def symptom_detail(request, symptom_id):
    patient = Patient.objects.filter(user=request.user).first()
    symptom = get_object_or_404(Symptom, id=symptom_id)
    if symptom.patient != patient:
        if not (symptom.patient.family and symptom.patient.family.head == patient):
            return HttpResponseForbidden("Not authorized.")
    return render(request, 'patient/symptom_detail.html', {'symptom': symptom, 'patient': patient})

def delete_symptom(request, symptom_id):
    import django.contrib.messages as messages
    patient = Patient.objects.filter(user=request.user).first()
    symptom = get_object_or_404(Symptom, id=symptom_id, patient=patient)
    if symptom.ai_prediction_status == 'PENDING_REVIEW':
        symptom.is_archived = True
        symptom.save()
        messages.success(request, 'Record archived successfully.')
    else:
        messages.error(request, 'Cannot archive a verified medical record.')
    return redirect('patient_dashboard')
