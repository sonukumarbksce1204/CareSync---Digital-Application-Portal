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

def doctor_dashboard(request):
    doctor = get_session_doctor(request)
    if not doctor:
        request.session.flush()
        return redirect("doctor_login")

    return render(request, "doctor/dashboard.html", {"doctor": doctor})


def doctor_logout(request):
    request.session.flush()
    return redirect("doctor_login")


def doctor_profile(request):
    doctor = get_session_doctor(request)
    if not doctor:
        request.session.flush()
        return redirect("doctor_login")

    if request.method == "POST":
        image = request.FILES.get("profile_image")
        if image:
            doctor.profile_image = image
            doctor.save()

    qualifications = doctor.qualifications.all()
    specializations = doctor.specializations.all()

    return render(request, "doctor/profile.html", {
        "doctor": doctor,
        "qualifications": qualifications,
        "specializations": specializations
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
    return render(request, 'doctor/patient_result.html', {'patient': patient, 'doctor': doctor})