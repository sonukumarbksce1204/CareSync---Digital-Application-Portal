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
        request.session.flush()
        return redirect("admin_login")

    from doctor.models import Doctor, DoctorVerification
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

        return redirect("admin_doctors")

    doctors = Doctor.objects.all().prefetch_related(
        'specializations', 'qualifications'
    ).select_related('verification').order_by('-created_at')

    return render(request, "admin_panel/admin_doctors.html", {
        "admin": admin,
        "doctors": doctors,
    })


# ── Hospital Management ───────────────────────────────────────────────────────

def admin_hospitals(request):
    admin = get_session_admin(request)
    if not admin:
        request.session.flush()
        return redirect("admin_login")

    from hospital.models import Hospital
    hospitals = Hospital.objects.all().order_by('-registration_date')

    return render(request, "admin_panel/admin_hospitals.html", {
        "admin": admin,
        "hospitals": hospitals,
    })


# ── Patient Management ────────────────────────────────────────────────────────

def admin_patients(request):
    admin = get_session_admin(request)
    if not admin:
        request.session.flush()
        return redirect("admin_login")

    from patient.models import Patient
    patients = Patient.objects.select_related('user').all().order_by('-created_at')

    return render(request, "admin_panel/admin_patients.html", {
        "admin": admin,
        "patients": patients,
    })


# ── Disease Mappings ─────────────────────────────────────────────────────────

def disease_mappings(request):
    admin = get_session_admin(request)
    if not admin:
        request.session.flush()
        return redirect("admin_login")

    from .models import DiseaseSpecialtyMapping

    if request.method == "POST":
        disease_name = request.POST.get("disease_name", "").strip()
        specialty_name = request.POST.get("specialty_name", "").strip()

        if disease_name and specialty_name:
            # Simple upsert
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
