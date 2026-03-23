from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import AdminUser


def get_session_admin(request):
    admin_id = request.session.get("admin_id")
    if not admin_id:
        return None
    return AdminUser.objects.filter(id=admin_id).first()


# ── Login / Logout ────────────────────────────────────────────────────────────

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
