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


def doctor_dashboard(request):
    doctor_id = request.session.get("doctor_id")

    if not doctor_id:
        return redirect("doctor_login")

    doctor = Doctor.objects.get(doctor_id=doctor_id)

    return render(request, "doctor/dashboard.html", {"doctor": doctor})


def doctor_logout(request):
    request.session.flush()
    return redirect("doctor_login")


def doctor_profile(request):
    doctor_id = request.session.get("doctor_id")

    if not doctor_id:
        return redirect("doctor_login")

    doctor = Doctor.objects.get(doctor_id=doctor_id)

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