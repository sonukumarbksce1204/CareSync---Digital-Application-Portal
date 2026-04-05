from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import AdminUser


def get_session_admin(request):
    admin_id = request.session.get("admin_id")
    if not admin_id:
        return None
    return AdminUser.objects.filter(id=admin_id).first()


# ── Login / Logout ────────────────────────────────────────────────────────────

def signup_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "admin_panel/admin_signup.html")

        if AdminUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, "admin_panel/admin_signup.html")

        if AdminUser.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return render(request, "admin_panel/admin_signup.html")

        admin = AdminUser(username=username, email=email)
        admin.set_password(password)
        admin.save()

        messages.success(request, "Admin account created successfully. Please sign in.")
        return redirect("admin_login")

    return render(request, "admin_panel/admin_signup.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        try:
            admin = AdminUser.objects.get(username=username)
            if admin.check_password(password):
                request.session["admin_id"] = admin.id
                return redirect("admin_dashboard")
            else:
                messages.error(request, "Invalid password.")
        except AdminUser.DoesNotExist:
            messages.error(request, "Admin account not found.")

    return render(request, "admin_panel/admin_login.html")


def admin_logout(request):
    request.session.flush()
    return redirect("admin_login")


# ── Dashboard ─────────────────────────────────────────────────────────────────

def dashboard(request):
    admin = get_session_admin(request)
    if not admin:
        request.session.flush()
        return redirect("admin_login")

    from patient.models import Patient
    from doctor.models import Doctor, DoctorVerification
    from hospital.models import Hospital

    stats = {
        'total_patients': Patient.objects.count(),
        'total_doctors': Doctor.objects.count(),
        'total_hospitals': Hospital.objects.count(),
        'pending_verifications': DoctorVerification.objects.filter(verified_by_admin=False).count(),
    }

    recent_doctors = Doctor.objects.filter(
        verification_status='pending'
    ).prefetch_related('qualifications', 'specializations').order_by('-created_at')[:5]

    return render(request, "admin_panel/admin_dashboard.html", {
        "admin": admin,
        "stats": stats,
        "recent_doctors": recent_doctors,
    })


# ── Doctor Management ─────────────────────────────────────────────────────────

def admin_doctors(request):
    admin = get_session_admin(request)
    if not admin:
        return redirect("admin_login")

    from doctor.models import Doctor, DoctorVerification, Specialization
    from django.utils import timezone

    if request.method == "POST":
        action = request.POST.get("action")
        doc_id = request.POST.get("doctor_id")
        doctor = get_object_or_404(Doctor, id=doc_id)

        if action == "VERIFY":
            doctor.verification_status = "verified"
            doctor.save(update_fields=["verification_status"])
            if hasattr(doctor, "verification"):
                DoctorVerification.objects.filter(doctor=doctor).update(
                    verified_by_admin=True, verified_at=timezone.now()
                )
            messages.success(request, f"Dr. {doctor.full_name} has been verified.")

        elif action == "REJECT":
            doctor.verification_status = "rejected"
            doctor.save(update_fields=["verification_status"])
            if hasattr(doctor, "verification"):
                DoctorVerification.objects.filter(doctor=doctor).update(
                    verified_by_admin=False, verified_at=None
                )
            messages.success(request, f"Dr. {doctor.full_name}'s verification rejected.")

        elif action == "TOGGLE_STATUS":
            doctor.profile_status = "inactive" if doctor.profile_status == "active" else "active"
            doctor.save(update_fields=["profile_status"])
            messages.success(request, f"Dr. {doctor.full_name} status changed to {doctor.profile_status}.")

        elif action == "DELETE":
            name = doctor.full_name
            doctor.delete()
            messages.success(request, f"Dr. {name} has been permanently deleted.")

        return redirect("admin_doctors")

    q = request.GET.get("q", "").strip()
    doctors = Doctor.objects.all().prefetch_related(
        'specializations', 'qualifications'
    ).select_related('verification').order_by('-created_at')
    if q:
        from django.db.models import Q
        doctors = doctors.filter(Q(full_name__icontains=q) | Q(email__icontains=q))

    from doctor.models import Specialization
    all_specs = Specialization.objects.all().order_by('name')

    return render(request, "admin_panel/admin_doctors.html", {
        "admin": admin,
        "doctors": doctors,
        "q": q,
        "all_specs": all_specs,
    })


def admin_doctor_edit(request, doctor_id):
    admin = get_session_admin(request)
    if not admin:
        return redirect("admin_login")

    from doctor.models import Doctor, Specialization
    doctor = get_object_or_404(Doctor, id=doctor_id)
    all_specs = Specialization.objects.all().order_by('name')

    if request.method == "POST":
        doctor.full_name = request.POST.get("full_name", doctor.full_name).strip()
        doctor.email = request.POST.get("email", doctor.email).strip()
        doctor.phone = request.POST.get("phone", doctor.phone).strip()
        doctor.experience_years = int(request.POST.get("experience_years", doctor.experience_years) or doctor.experience_years)
        selected_specs = request.POST.getlist("specializations")
        doctor.save()
        if selected_specs:
            doctor.specializations.set(selected_specs)
        messages.success(request, f"Dr. {doctor.full_name}'s profile updated.")
        return redirect("admin_doctors")

    return render(request, "admin_panel/admin_doctor_edit.html", {
        "admin": admin,
        "doctor": doctor,
        "all_specs": all_specs,
    })


# ── Hospital Management ───────────────────────────────────────────────────────

def admin_hospitals(request):
    admin = get_session_admin(request)
    if not admin:
        return redirect("admin_login")

    from hospital.models import Hospital

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "DELETE":
            h = get_object_or_404(Hospital, id=request.POST.get("hospital_id"))
            name = h.name
            h.delete()
            messages.success(request, f"Hospital '{name}' deleted.")
            return redirect("admin_hospitals")

        if action == "CREATE":
            name = request.POST.get("name", "").strip()
            reg_no = request.POST.get("registration_number", "").strip()
            htype = request.POST.get("hospital_type", "Private")
            address = request.POST.get("address", "").strip()
            city = request.POST.get("city", "").strip()
            state = request.POST.get("state", "").strip()
            pincode = request.POST.get("pincode", "").strip()
            contact = request.POST.get("contact_number", "").strip()
            email = request.POST.get("email", "").strip()
            website = request.POST.get("website", "").strip() or None
            beds = int(request.POST.get("total_beds", 0) or 0)
            emergency = request.POST.get("emergency_services") == "on"
            password = request.POST.get("password", "").strip()

            if not all([name, reg_no, address, city, state, pincode, contact, email, password]):
                messages.error(request, "All required fields must be filled.")
                return redirect("admin_hospitals")

            if Hospital.objects.filter(registration_number=reg_no).exists():
                messages.error(request, "Registration number already exists.")
                return redirect("admin_hospitals")

            if Hospital.objects.filter(email=email).exists():
                messages.error(request, "Email already registered.")
                return redirect("admin_hospitals")

            Hospital.objects.create(
                name=name, registration_number=reg_no, hospital_type=htype,
                address=address, city=city, state=state, pincode=pincode,
                contact_number=contact, email=email, website=website,
                total_beds=beds, emergency_services=emergency, password=password
            )
            messages.success(request, f"Hospital '{name}' created successfully.")
            return redirect("admin_hospitals")

    q = request.GET.get("q", "").strip()
    hospitals = Hospital.objects.all().order_by('-registration_date')
    if q:
        from django.db.models import Q
        hospitals = hospitals.filter(Q(name__icontains=q) | Q(city__icontains=q) | Q(state__icontains=q))

    return render(request, "admin_panel/admin_hospitals.html", {
        "admin": admin,
        "hospitals": hospitals,
        "q": q,
    })


def admin_hospital_edit(request, hospital_id):
    admin = get_session_admin(request)
    if not admin:
        return redirect("admin_login")

    from hospital.models import Hospital
    hospital = get_object_or_404(Hospital, id=hospital_id)

    if request.method == "POST":
        hospital.name = request.POST.get("name", hospital.name).strip()
        hospital.hospital_type = request.POST.get("hospital_type", hospital.hospital_type)
        hospital.address = request.POST.get("address", hospital.address).strip()
        hospital.city = request.POST.get("city", hospital.city).strip()
        hospital.state = request.POST.get("state", hospital.state).strip()
        hospital.pincode = request.POST.get("pincode", hospital.pincode).strip()
        hospital.contact_number = request.POST.get("contact_number", hospital.contact_number).strip()
        hospital.email = request.POST.get("email", hospital.email).strip()
        hospital.website = request.POST.get("website", "").strip() or None
        hospital.total_beds = int(request.POST.get("total_beds", hospital.total_beds) or 0)
        hospital.emergency_services = request.POST.get("emergency_services") == "on"
        hospital.established_year = request.POST.get("established_year") or hospital.established_year

        # Only update password if provided
        new_pw = request.POST.get("new_password", "").strip()
        if new_pw:
            from django.contrib.auth.hashers import make_password
            hospital.password = make_password(new_pw)

        # Call super().save() directly to avoid double-hashing
        from django.db.models import Model
        Model.save(hospital)
        messages.success(request, f"Hospital '{hospital.name}' updated.")
        return redirect("admin_hospitals")

    return render(request, "admin_panel/admin_hospital_edit.html", {
        "admin": admin,
        "hospital": hospital,
    })


# ── Patient Management ────────────────────────────────────────────────────────

def admin_patients(request):
    admin = get_session_admin(request)
    if not admin:
        return redirect("admin_login")

    from patient.models import Patient

    if request.method == "POST":
        action = request.POST.get("action")
        patient_id = request.POST.get("patient_id")
        patient = get_object_or_404(Patient, id=patient_id)

        if action == "TOGGLE_ACTIVE":
            patient.user.is_active = not patient.user.is_active
            patient.user.save(update_fields=["is_active"])
            state = "activated" if patient.user.is_active else "deactivated"
            messages.success(request, f"Patient {patient.user.get_full_name() or patient.user.username} {state}.")

        elif action == "DELETE":
            name = patient.user.get_full_name() or patient.user.username
            patient.user.delete()   # cascades to Patient via OneToOne
            messages.success(request, f"Patient '{name}' permanently deleted.")

        return redirect("admin_patients")

    q = request.GET.get("q", "").strip()
    patients = Patient.objects.select_related('user').all().order_by('-created_at')
    if q:
        from django.db.models import Q
        patients = patients.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__email__icontains=q) |
            Q(patient_id__icontains=q) |
            Q(phone__icontains=q)
        )

    return render(request, "admin_panel/admin_patients.html", {
        "admin": admin,
        "patients": patients,
        "q": q,
    })


def admin_patient_edit(request, patient_id):
    admin = get_session_admin(request)
    if not admin:
        return redirect("admin_login")

    from patient.models import Patient
    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == "POST":
        # Update Django User fields
        patient.user.first_name = request.POST.get("first_name", patient.user.first_name).strip()
        patient.user.last_name = request.POST.get("last_name", patient.user.last_name).strip()
        patient.user.email = request.POST.get("email", patient.user.email).strip()
        patient.user.save(update_fields=["first_name", "last_name", "email"])

        # Update Patient profile fields
        patient.phone = request.POST.get("phone", patient.phone).strip()
        patient.age = request.POST.get("age") or patient.age
        patient.gender = request.POST.get("gender", patient.gender)
        patient.blood_group = request.POST.get("blood_group", patient.blood_group).strip()
        patient.address = request.POST.get("address", patient.address).strip()
        patient.emergency_contact = request.POST.get("emergency_contact", patient.emergency_contact).strip()
        patient.save()

        messages.success(request, f"Patient {patient.user.get_full_name()} updated successfully.")
        return redirect("admin_patients")

    return render(request, "admin_panel/admin_patient_edit.html", {
        "admin": admin,
        "patient": patient,
    })


# ── Disease Mappings ─────────────────────────────────────────────────────────

def disease_mappings(request):
    admin = get_session_admin(request)
    if not admin:
        return redirect("admin_login")

    from .models import DiseaseSpecialtyMapping

    if request.method == "POST":
        disease_name = request.POST.get("disease_name", "").strip()
        specialty_name = request.POST.get("specialty_name", "").strip()

        if disease_name and specialty_name:
            mapping, created = DiseaseSpecialtyMapping.objects.update_or_create(
                disease_name__iexact=disease_name,
                defaults={
                    'disease_name': disease_name,
                    'specialty_name': specialty_name
                }
            )
            messages.success(request, f"Mapping created: {disease_name} -> {specialty_name}")
        else:
            messages.error(request, "Both fields are required.")
        return redirect("admin_disease_mappings")

    mappings = DiseaseSpecialtyMapping.objects.all().order_by('-created_at')

    return render(request, "admin_panel/disease_mappings.html", {
        "admin": admin,
        "mappings": mappings,
    })

def delete_disease_mapping(request, mapping_id):
    admin = get_session_admin(request)
    if not admin:
        return redirect("admin_login")

    from .models import DiseaseSpecialtyMapping
    mapping = get_object_or_404(DiseaseSpecialtyMapping, id=mapping_id)
    mapping.delete()
    messages.success(request, "Mapping deleted successfully.")
    return redirect("admin_disease_mappings")
