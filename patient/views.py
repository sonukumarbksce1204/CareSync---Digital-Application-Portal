from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from .forms import PatientSignUpForm, PatientProfileForm, SymptomForm
from .models import Patient, Family, Symptom
from hospital.models import Hospital


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
            patient__family=patient.family
        ).order_by("-created_at")
    else:
        symptoms = Symptom.objects.filter(
            patient=patient
        ).order_by("-created_at")

    return render(request, "patient/patient_dashboard.html", {
        "patient": patient,
        "hospitals": hospitals,
        "symptoms": symptoms,
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
        
    symptoms = target.symptoms.all().order_by('-created_at')
    return render(request, 'patient/member_history.html', {'member': target, 'symptoms': symptoms})

