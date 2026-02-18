from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import PatientSignUpForm, PatientProfileForm, SymptomForm
from .models import Patient, Family, Symptom
from hospital.models import Hospital


# ==============================
# PATIENT SIGNUP
# ==============================
def patient_signup(request):
    if request.method == "POST":
        user_form = PatientSignUpForm(request.POST)
        profile_form = PatientProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():

            # Save user (password already hashed inside form)
            user = user_form.save()

            # Save patient profile
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()

            # Auto login
            login(request, user)
            return redirect('patient_dashboard')

    else:
        user_form = PatientSignUpForm()
        profile_form = PatientProfileForm()

    return render(request, 'patient/patient_signup.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


# ==============================
# PATIENT LOGIN
# ==============================
def patient_login(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('patient_dashboard')
        else:
            return render(request, 'patient/patient_login.html', {
                'error': 'Invalid credentials'
            })

    return render(request, 'patient/patient_login.html')


# ==============================
# PATIENT DASHBOARD
# ==============================
def patient_dashboard(request):

    if not request.user.is_authenticated:
        return redirect('patient_login')

    patient = Patient.objects.filter(user=request.user).first()
    if not patient:
        return redirect('patient_signup')

    hospitals = Hospital.objects.all()[:6]
    message = None

    if request.method == "POST":

        # Join Family
        if "join_family" in request.POST:
            entered_id = request.POST.get("family_id")
            family = Family.objects.filter(family_id=entered_id).first()

            if family:
                patient.family = family
                patient.save()
                message = "Connected to family successfully."
            else:
                message = "Invalid Family ID."

        # Generate New Family
        elif "generate_family" in request.POST:
            if not patient.family:
                family = Family.objects.create(head=patient)
                patient.family = family
                patient.save()
                message = "New Family created successfully."
            else:
                message = "You are already connected to a family."

        # Add Symptom
        elif "add_symptom" in request.POST:
            form = SymptomForm(request.POST, request.FILES)
            if form.is_valid():
                symptom = form.save(commit=False)
                symptom.patient = patient
                symptom.save()
                message = "Medical record added successfully."

    # ==============================
    # CONTROLLED ACCESS LOGIC
    # ==============================
    if patient.family and patient.family.head == patient:
        # Family head sees all family records
        symptoms = Symptom.objects.filter(
            patient__family=patient.family
        ).order_by("-created_at")
    else:
        # Normal member sees only own records
        symptoms = Symptom.objects.filter(
            patient=patient
        ).order_by("-created_at")

    symptom_form = SymptomForm()

    return render(request, "patient/patient_dashboard.html", {
        "patient": patient,
        "hospitals": hospitals,
        "symptoms": symptoms,
        "symptom_form": symptom_form,
        "message": message
    })


# ==============================
# PATIENT LOGOUT
# ==============================
def patient_logout(request):
    logout(request)
    return redirect('patient_login')
