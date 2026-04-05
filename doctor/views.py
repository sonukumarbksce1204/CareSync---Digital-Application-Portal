from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse

from .models import Doctor, Specialization, DoctorVerification, Qualification, HospitalAffiliation, DoctorAvailabilitySlot
from .forms import DoctorProfileUpdateForm, ConsultationForm, AIReviewForm

from patient.models import (
    Appointment, Patient, Family, Symptom,
    DoctorAccessLog, AIReviewLog, ConsultationRecord, PatientDisease, DiseaseCatalog
)
from patient.services.access_service import log_doctor_access
from patient.services.family_service import get_family_disease_summary
from hospital.models import Hospital


# ── Session Helper ────────────────────────────────────────────────────────────

def get_session_doctor(request):
    doctor_id = request.session.get("doctor_id")
    if not doctor_id:
        return None
    return Doctor.objects.filter(doctor_id=doctor_id).first()


# ── Signup ────────────────────────────────────────────────────────────────────

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
        custom_specs = request.POST.get("custom_specialization")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return render(request, "doctor/signup.html", {"specializations": specializations})

        if Doctor.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return render(request, "doctor/signup.html", {"specializations": specializations})

        if Doctor.objects.filter(phone=phone).exists():
            messages.error(request, "Phone number already registered")
            return render(request, "doctor/signup.html", {"specializations": specializations})

        if DoctorVerification.objects.filter(license_number=license_number).exists():
            messages.error(request, "License number already registered")
            return render(request, "doctor/signup.html", {"specializations": specializations})

        doctor = Doctor(full_name=full_name, email=email, phone=phone, experience_years=experience)
        doctor.set_password(password)
        doctor.save()
        
        if custom_specs:
            for spec_name in custom_specs.split(','):
                spec_name = spec_name.strip()
                if spec_name:
                    spec_obj, _ = Specialization.objects.get_or_create(name=spec_name)
                    selected_specs.append(spec_obj.id)
                    
        doctor.specializations.set(selected_specs)

        DoctorVerification.objects.create(
            doctor=doctor,
            license_number=license_number,
            license_document=license_file
        )

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


# ── Login / Logout ────────────────────────────────────────────────────────────

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


def doctor_logout(request):
    request.session.flush()
    return redirect("doctor_login")


# ── Dashboard ─────────────────────────────────────────────────────────────────

def doctor_dashboard(request):
    doctor = get_session_doctor(request)
    if not doctor:
        request.session.flush()
        return redirect("doctor_login")

    pending_appointments = Appointment.objects.filter(doctor=doctor, status='REQUESTED').count()
    upcoming_appointments = Appointment.objects.filter(
        doctor=doctor, status='APPROVED', preferred_date__gte=timezone.now().date()
    ).count()

    accessed_patient_ids = DoctorAccessLog.objects.filter(doctor=doctor).values_list('patient_id', flat=True)
    apt_patient_ids = Appointment.objects.filter(
        doctor=doctor, status__in=['APPROVED', 'COMPLETED']
    ).values_list('patient_id', flat=True)
    my_patients_count = Patient.objects.filter(
        Q(id__in=accessed_patient_ids) | Q(id__in=apt_patient_ids)
    ).distinct().count()

    pending_reviews_count = Symptom.objects.filter(
        patient__id__in=accessed_patient_ids, ai_prediction_status='PENDING_REVIEW'
    ).count()

    return render(request, "doctor/dashboard.html", {
        "doctor": doctor,
        "pending_appointments": pending_appointments,
        "upcoming_appointments": upcoming_appointments,
        "my_patients_count": my_patients_count,
        "pending_reviews_count": pending_reviews_count,
    })


# ── Profile ───────────────────────────────────────────────────────────────────

def doctor_profile(request):
    doctor = get_session_doctor(request)
    if not doctor:
        request.session.flush()
        return redirect("doctor_login")

    if request.method == "POST":
        if 'add_qualification' in request.POST:
            degree = request.POST.get('degree')
            institution = request.POST.get('institution')
            year = request.POST.get('year_completed')
            if degree and institution and year:
                Qualification.objects.create(
                    doctor=doctor, degree=degree, institution=institution, year_completed=year
                )
                messages.success(request, "Qualification added.")
            return redirect('doctor_profile')
            
        if 'delete_qualification' in request.POST:
            q_id = request.POST.get('q_id')
            Qualification.objects.filter(id=q_id, doctor=doctor).delete()
            messages.success(request, "Qualification removed.")
            return redirect('doctor_profile')

        form = DoctorProfileUpdateForm(request.POST, request.FILES, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('doctor_profile')
    else:
        form = DoctorProfileUpdateForm(instance=doctor)

    return render(request, "doctor/profile.html", {
        "doctor": doctor,
        "form": form,
        "qualifications": doctor.qualifications.all(),
        "specializations": doctor.specializations.all(),
        "affiliations": doctor.affiliations.filter(status='APPROVED'),
    })


# ── Patient Search ────────────────────────────────────────────────────────────

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
                return render(request, 'doctor/family_result.html', {
                    'family': family, 'summary': summary, 'doctor': doctor
                })

        elif search_type == 'personal':
            patient = Patient.objects.filter(patient_id=query).first()
            if patient:
                log_doctor_access(doctor, 'PERSONAL', patient=patient)
                if request.GET.get('expand') == 'true' and patient.family:
                    log_doctor_access(doctor, 'EXPANDED', patient=patient, family=patient.family)
                    summary = get_family_disease_summary(patient.family)
                    return render(request, 'doctor/family_result.html', {
                        'family': patient.family, 'summary': summary, 'doctor': doctor
                    })
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
    consultations = ConsultationRecord.objects.filter(patient=patient).order_by('-created_at')

    return render(request, 'doctor/patient_result.html', {
        'patient': patient,
        'doctor': doctor,
        'consultations': consultations,
    })


# ── AI Review ─────────────────────────────────────────────────────────────────

def review_prediction(request, symptom_id):
    doctor = get_session_doctor(request)
    if not doctor:
        return redirect('doctor_login')

    symptom = get_object_or_404(Symptom, id=symptom_id)

    # Authorization: must have accessed patient via Health ID or approved appointment
    has_access = DoctorAccessLog.objects.filter(doctor=doctor, patient=symptom.patient).exists()
    has_apt = Appointment.objects.filter(
        doctor=doctor, patient=symptom.patient, status__in=['APPROVED', 'COMPLETED']
    ).exists()
    if not (has_access or has_apt):
        messages.error(request, "You are not authorized to review this record.")
        return redirect('doctor_search')

    old_status = symptom.ai_prediction_status
    old_catalog_id = symptom.doctor_final_diagnosis_catalog_id

    if request.method == 'POST':
        form = AIReviewForm(request.POST, instance=symptom)
        if form.is_valid():
            sympt = form.save(commit=False)
            sympt.verified_by_doctor = doctor
            sympt.verified_at = timezone.now()
            sympt.save()

            new_catalog = sympt.doctor_final_diagnosis_catalog
            AIReviewLog.objects.create(
                symptom=sympt,
                doctor=doctor,
                previous_status=old_status,
                new_status=sympt.ai_prediction_status,
                previous_diagnosis_text=sympt.predicted_disease,
                new_diagnosis_text=(
                    new_catalog.name if new_catalog else sympt.doctor_modified_diagnosis_text
                ),
                previous_catalog_id=old_catalog_id,
                new_catalog_id=new_catalog.id if new_catalog else None,
                note=sympt.verification_note,
            )
            messages.success(request, "AI Prediction verified successfully.")
            return redirect('doctor_patient_detail', patient_id=symptom.patient.patient_id)
    else:
        form = AIReviewForm(instance=symptom)

    return render(request, 'doctor/review_prediction.html', {
        'form': form,
        'symptom': symptom,
        'doctor': doctor,
    })


# ── Appointments ──────────────────────────────────────────────────────────────

def doctor_appointments(request):
    doctor = get_session_doctor(request)
    if not doctor:
        return redirect("doctor_login")

    if request.method == "POST" and "reschedule_action" in request.POST:
        apt_id = request.POST.get("apt_id")
        action = request.POST.get("reschedule_action")
        apt = get_object_or_404(Appointment, id=apt_id, doctor=doctor)
        
        if not apt.hospital:
            if action == 'PROPOSE':
                apt.reschedule_requested_by = 'DOCTOR'
                apt.reschedule_date = request.POST.get('reschedule_date') or None
                apt.reschedule_time = request.POST.get('reschedule_time') or None
                apt.reschedule_reason = request.POST.get('reschedule_reason')
                apt.save()
                messages.success(request, "Reschedule proposal sent to patient.")
            elif action == 'ACCEPT' and apt.reschedule_requested_by == 'PATIENT':
                apt.preferred_date = apt.reschedule_date
                if apt.reschedule_time:
                    apt.appointment_time = apt.reschedule_time
                apt.reschedule_requested_by = None
                apt.reschedule_date = None
                apt.reschedule_time = None
                apt.reschedule_reason = None
                apt.save()
                messages.success(request, "Patient reschedule request accepted.")
            elif action == 'REJECT' and apt.reschedule_requested_by == 'PATIENT':
                apt.reschedule_requested_by = None
                apt.reschedule_date = None
                apt.reschedule_time = None
                apt.reschedule_reason = None
                apt.save()
                messages.success(request, "Patient reschedule request rejected.")
        return redirect('doctor_appointments')

    today = timezone.now().date()

    requested = Appointment.objects.filter(doctor=doctor, status='REQUESTED').order_by('preferred_date')
    upcoming = Appointment.objects.filter(
        doctor=doctor, status='APPROVED', preferred_date__gte=today
    ).order_by('preferred_date')
    past_completed = Appointment.objects.filter(
        doctor=doctor, status='COMPLETED'
    ).order_by('-preferred_date')
    cancelled = Appointment.objects.filter(
        doctor=doctor, status__in=['CANCELLED', 'REJECTED']
    ).order_by('-preferred_date')

    return render(request, "doctor/appointments.html", {
        "doctor": doctor,
        "requested": requested,
        "upcoming": upcoming,
        "past_completed": past_completed,
        "cancelled": cancelled,
    })


def update_appointment_status(request, apt_id, target_status):
    """POST-only. Valid transitions:
       REQUESTED → APPROVED, REJECTED
       APPROVED  → CANCELLED
       (COMPLETED only via save_consultation)
    Uses select_for_update() so concurrent approvals are safe.
    """
    if request.method != "POST":
        return redirect('doctor_appointments')

    doctor = get_session_doctor(request)
    if not doctor:
        return redirect("doctor_login")

    from django.db import transaction

    with transaction.atomic():
        apt = Appointment.objects.select_for_update().filter(id=apt_id, doctor=doctor).first()
        if not apt:
            messages.error(request, "Appointment not found.")
            return redirect('doctor_appointments')

        valid_transitions = {
            'REQUESTED': ['APPROVED', 'REJECTED'],
            'APPROVED': ['CANCELLED'],
        }

        if apt.status in valid_transitions and target_status in valid_transitions[apt.status]:
            # Lock the linked slot if it exists
            slot = None
            if apt.slot_id:
                slot = DoctorAvailabilitySlot.objects.select_for_update().filter(id=apt.slot_id).first()

            if target_status == 'APPROVED':
                # Ensure no other APPROVED appointment overlaps this slot for this doctor
                if slot:
                    if slot.status == 'BOOKED':
                        messages.error(request, "This slot was already booked by someone else.")
                        return redirect('doctor_appointments')
                    slot.status = 'BOOKED'
                    slot.save()
                apt.approved_at = timezone.now()
                meeting_info = request.POST.get('meeting_link_or_address', '').strip()
                if meeting_info and not apt.hospital:
                    apt.meeting_link_or_address = meeting_info

            elif target_status == 'REJECTED':
                if slot:
                    slot.status = 'AVAILABLE'
                    slot.save()
                apt.rejected_at = timezone.now()
                apt.rejection_reason = request.POST.get('rejection_reason', '').strip() or None

            elif target_status == 'CANCELLED':
                if slot:
                    slot.status = 'AVAILABLE'
                    slot.save()
                apt.cancelled_at = timezone.now()
                apt.cancellation_reason = request.POST.get('cancellation_reason', '').strip() or None

            apt.status = target_status
            apt.save()
            messages.success(request, f"Appointment {target_status.lower().replace('_', ' ')} successfully.")
        else:
            messages.error(request, "Invalid status transition.")

    return redirect('doctor_appointments')


# ── Slot Management ───────────────────────────────────────────────────────────

def manage_slots(request):
    doctor = get_session_doctor(request)
    if not doctor:
        return redirect("doctor_login")

    from django.db import transaction
    from datetime import date
    from hospital.models import Hospital

    if request.method == "POST":
        action = request.POST.get('action')

        if action == 'generate_slots':
            from doctor.models import DoctorWeeklyAvailability, DoctorLeave
            from datetime import date, timedelta
            
            weekly_rules = doctor.weekly_availability.all()
            if not weekly_rules.exists():
                messages.error(request, "No weekly repeating rules. Please add recurring availability first.")
            else:
                leaves = doctor.leaves.all()
                today = date.today()
                slots_created = 0
                
                # We will check existing closures here inside the loop dynamically since Hospital is queried anyway.
                from hospital.models import HospitalClosure

                for day_offset in range(30):
                    current_date = today + timedelta(days=day_offset)
                    
                    if leaves.filter(start_date__lte=current_date, end_date__gte=current_date).exists():
                        continue
                        
                    day_idx = current_date.weekday()
                    rules_for_day = weekly_rules.filter(day_of_week=day_idx)
                    
                    for rule in rules_for_day:
                        if rule.hospital and HospitalClosure.objects.filter(
                            hospital=rule.hospital, start_date__lte=current_date, end_date__gte=current_date
                        ).exists():
                            continue
                            
                        from datetime import datetime, time, timedelta as td

                        start_dt = datetime.combine(current_date, rule.start_time)
                        end_dt = datetime.combine(current_date, rule.end_time)
                        interval_td = td(minutes=rule.interval_minutes)
                        
                        current_dt = start_dt
                        while current_dt + interval_td <= end_dt:
                            slot_start_time = current_dt.time()
                            slot_end_time = (current_dt + interval_td).time()
                            
                            with transaction.atomic():
                                if not DoctorAvailabilitySlot.objects.filter(
                                    doctor=doctor, date=current_date, start_time=slot_start_time
                                ).exists():
                                    DoctorAvailabilitySlot.objects.create(
                                        doctor=doctor,
                                        date=current_date,
                                        start_time=slot_start_time,
                                        end_time=slot_end_time,
                                        hospital=rule.hospital,
                                        visit_mode=rule.visit_mode,
                                        status='AVAILABLE'
                                    )
                                    slots_created += 1
                                    
                            current_dt += interval_td
                                
                messages.success(request, f"Generated {slots_created} fractional slots for the next 30 days.")

        elif action == 'add_weekly_rule':
            from doctor.models import DoctorWeeklyAvailability
            day_of_week = request.POST.get('day_of_week')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            hospital_id = request.POST.get('hospital_id') or None
            visit_mode = request.POST.get('visit_mode') or None
            interval_minutes = int(request.POST.get('interval_minutes', 30))
            
            if day_of_week and start_time and end_time:
                hospital = Hospital.objects.filter(id=hospital_id).first() if hospital_id else None
                DoctorWeeklyAvailability.objects.create(
                    doctor=doctor, day_of_week=day_of_week, start_time=start_time, end_time=end_time,
                    interval_minutes=interval_minutes, hospital=hospital, visit_mode=visit_mode
                )
                messages.success(request, f"Weekly availability rule added with {interval_minutes}m slots.")
            else:
                messages.error(request, "Missing fields for weekly rule.")
                
        elif action == 'delete_weekly_rule':
            from doctor.models import DoctorWeeklyAvailability
            rule_id = request.POST.get('rule_id')
            DoctorWeeklyAvailability.objects.filter(id=rule_id, doctor=doctor).delete()
            messages.success(request, "Weekly availability rule removed.")

        elif action == 'add_leave':
            from doctor.models import DoctorLeave
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            reason = request.POST.get('reason', '')
            if start_date and end_date:
                DoctorLeave.objects.create(doctor=doctor, start_date=start_date, end_date=end_date, reason=reason)
                messages.success(request, "Leave / override dates marked.")
            else:
                messages.error(request, "Start and end dates are required.")

        elif action == 'delete_leave':
            from doctor.models import DoctorLeave
            leave_id = request.POST.get('leave_id')
            DoctorLeave.objects.filter(id=leave_id, doctor=doctor).delete()
            messages.success(request, "Leave removed.")

        elif action == 'create':
            slot_date = request.POST.get('date')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            hospital_id = request.POST.get('hospital_id') or None
            visit_mode = request.POST.get('visit_mode') or None
            interval_minutes = int(request.POST.get('interval_minutes', 30))

            if not (slot_date and start_time and end_time):
                messages.error(request, "Date, start time, and end time are required.")
                return redirect('doctor_manage_slots')

            try:
                from datetime import date as _date, datetime
                parsed_date = date.fromisoformat(slot_date)
                if parsed_date < date.today():
                    messages.error(request, "Cannot create slots in the past.")
                    return redirect('doctor_manage_slots')
            except ValueError:
                messages.error(request, "Invalid date.")
                return redirect('doctor_manage_slots')

            hospital = Hospital.objects.filter(id=hospital_id).first() if hospital_id else None

            from datetime import datetime, timedelta as td
            try:
                start_dt = datetime.combine(parsed_date, datetime.strptime(start_time, '%H:%M').time())
                end_dt = datetime.combine(parsed_date, datetime.strptime(end_time, '%H:%M').time())
            except ValueError:
                # Fallback if seconds are included
                start_dt = datetime.combine(parsed_date, datetime.strptime(start_time, '%H:%M:%S').time())
                end_dt = datetime.combine(parsed_date, datetime.strptime(end_time, '%H:%M:%S').time())

            interval_td = td(minutes=interval_minutes)
            current_dt = start_dt
            slots_created = 0

            with transaction.atomic():
                while current_dt + interval_td <= end_dt:
                    slot_start = current_dt.time()
                    slot_end = (current_dt + interval_td).time()
                    
                    overlap = Appointment.objects.filter(
                        doctor=doctor,
                        preferred_date=slot_date,
                        appointment_time=slot_start,
                        status__in=['REQUESTED', 'APPROVED']
                    ).exists()
                    
                    if not overlap:
                        _, created = DoctorAvailabilitySlot.objects.get_or_create(
                            doctor=doctor,
                            date=slot_date,
                            start_time=slot_start,
                            defaults={'end_time': slot_end, 'hospital': hospital, 'status': 'AVAILABLE', 'visit_mode': visit_mode}
                        )
                        if created:
                            slots_created += 1
                    current_dt += interval_td

            if slots_created > 0:
                messages.success(request, f"{slots_created} slot(s) created successfully.")
            else:
                messages.warning(request, "No new slots created. They may already exist or clash with appointments.")

        elif action == 'block':
            slot_id = request.POST.get('slot_id')
            slot = DoctorAvailabilitySlot.objects.filter(id=slot_id, doctor=doctor, status='AVAILABLE').first()
            if slot:
                slot.status = 'BLOCKED'
                slot.save()
                messages.success(request, "Slot blocked.")
            else:
                messages.error(request, "Slot not found or cannot be blocked.")

        elif action == 'unblock':
            slot_id = request.POST.get('slot_id')
            slot = DoctorAvailabilitySlot.objects.filter(id=slot_id, doctor=doctor, status='BLOCKED').first()
            if slot:
                slot.status = 'AVAILABLE'
                slot.save()
                messages.success(request, "Slot unblocked and is now available.")
            else:
                messages.error(request, "Slot not found or is not blocked.")

        elif action == 'delete':
            slot_id = request.POST.get('slot_id')
            with transaction.atomic():
                slot = DoctorAvailabilitySlot.objects.select_for_update().filter(
                    id=slot_id, doctor=doctor
                ).first()
                if not slot:
                    messages.error(request, "Slot not found.")
                elif slot.status in ('PENDING', 'BOOKED'):
                    messages.error(request, "Cannot delete a slot that has a pending or booked appointment.")
                else:
                    slot.delete()
                    messages.success(request, "Slot deleted.")

        return redirect('doctor_manage_slots')

    from datetime import date as _date
    all_slots = DoctorAvailabilitySlot.objects.filter(
        doctor=doctor, date__gte=_date.today()
    ).order_by('date', 'start_time').select_related('hospital', 'appointment_record__patient__user')

    affiliated_hospitals = HospitalAffiliation.objects.filter(
        doctor=doctor, status='APPROVED'
    ).select_related('hospital')

    return render(request, 'doctor/manage_slots.html', {
        'doctor': doctor,
        'slots': all_slots,
        'affiliated_hospitals': affiliated_hospitals,
        'slots_available': all_slots.filter(status='AVAILABLE').count(),
        'slots_pending': all_slots.filter(status='PENDING').count(),
        'slots_booked': all_slots.filter(status='BOOKED').count(),
        'slots_blocked': all_slots.filter(status='BLOCKED').count(),
        'weekly_rules': doctor.weekly_availability.all(),
        'leaves': doctor.leaves.all(),
    })


def get_doctor_slots_ajax(request):
    """AJAX: returns AVAILABLE slots for a doctor on a given date — used by patient booking."""
    doctor_id = request.GET.get('doctor_id')
    slot_date = request.GET.get('date')
    hospital_id = request.GET.get('hospital_id')  # optional filter for hospital booking
    if not doctor_id or not slot_date:
        return JsonResponse([], safe=False)

    qs = DoctorAvailabilitySlot.objects.filter(
        doctor__doctor_id=doctor_id,
        date=slot_date,
        status='AVAILABLE'
    )
    if hospital_id:
        # Filter to slots tied to this hospital or general (no hospital)
        qs = qs.filter(hospital_id=hospital_id) | DoctorAvailabilitySlot.objects.filter(
            doctor__doctor_id=doctor_id, date=slot_date, status='AVAILABLE', hospital__isnull=True
        )
        qs = qs.distinct()

    # Filter out leaves and closures real-time for an extra layer of safety
    from doctor.models import DoctorLeave
    if DoctorLeave.objects.filter(doctor__doctor_id=doctor_id, start_date__lte=slot_date, end_date__gte=slot_date).exists():
        return JsonResponse([], safe=False)
        
    from hospital.models import HospitalClosure
    if hospital_id:
        if HospitalClosure.objects.filter(hospital_id=hospital_id, start_date__lte=slot_date, end_date__gte=slot_date).exists():
            # If hospital closed, remove all hospital bound slots
            qs = qs.exclude(hospital_id=hospital_id)

    data = [
        {'id': s.id, 'start': str(s.start_time)[:5], 'end': str(s.end_time)[:5],
         'mode': s.visit_mode or ''}
        for s in qs.order_by('start_time')
    ]
    return JsonResponse(data, safe=False)


# ── My Patients ───────────────────────────────────────────────────────────────

def my_patients(request):
    doctor = get_session_doctor(request)
    if not doctor:
        return redirect("doctor_login")

    accessed_ids = DoctorAccessLog.objects.filter(doctor=doctor).values_list('patient_id', flat=True)
    apt_patient_ids = Appointment.objects.filter(
        doctor=doctor, status__in=['APPROVED', 'COMPLETED']
    ).values_list('patient_id', flat=True)

    patients = Patient.objects.filter(
        Q(id__in=accessed_ids) | Q(id__in=apt_patient_ids)
    ).distinct()

    query = request.GET.get('q', '').strip()
    if query:
        patients = patients.filter(
            Q(patient_id__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query)
        )

    return render(request, "doctor/my_patients.html", {"doctor": doctor, "patients": patients})


# ── Pending AI Reviews ────────────────────────────────────────────────────────

def pending_reviews(request):
    doctor = get_session_doctor(request)
    if not doctor:
        return redirect("doctor_login")

    accessed_ids = DoctorAccessLog.objects.filter(doctor=doctor).values_list('patient_id', flat=True)
    symptoms = Symptom.objects.filter(
        patient__id__in=accessed_ids, ai_prediction_status='PENDING_REVIEW'
    ).order_by('-created_at')

    return render(request, "doctor/pending_reviews.html", {"doctor": doctor, "symptoms": symptoms})


# ── Add Consultation ──────────────────────────────────────────────────────────

def add_consultation(request, patient_id):
    doctor = get_session_doctor(request)
    if not doctor:
        return redirect("doctor_login")

    patient = get_object_or_404(Patient, patient_id=patient_id)

    # Authorization: must have accessed patient or have an approved/completed appointment
    has_access = DoctorAccessLog.objects.filter(doctor=doctor, patient=patient).exists()
    has_apt = Appointment.objects.filter(
        doctor=doctor, patient=patient, status__in=['APPROVED', 'COMPLETED']
    ).exists()
    if not (has_access or has_apt):
        messages.error(request, "You are not authorized to consult this patient.")
        return redirect('doctor_search')

    # Build disease→is_hereditary map for JS warning
    diseases_json = {
        str(d.id): d.is_hereditary
        for d in DiseaseCatalog.objects.all()
    }

    # Pre-fill appointment from GET param
    preselected_apt_id = request.GET.get('appointment_id', '')

    if request.method == "POST":
        form = ConsultationForm(request.POST, request.FILES)
        if form.is_valid():
            consult = form.save(commit=False)
            consult.patient = patient
            consult.doctor = doctor

            apt_id = request.POST.get('appointment_id')
            if apt_id:
                apt = Appointment.objects.filter(
                    id=apt_id, doctor=doctor, patient=patient
                ).first()
                if apt and apt.status == 'APPROVED':
                    consult.appointment = apt
                    apt.status = 'COMPLETED'
                    apt.completed_at = timezone.now()
                    # Copy doctor instructions and follow_up_date from consultation to appointment
                    if consult.doctor_instructions:
                        apt.doctor_instructions = consult.doctor_instructions
                    if consult.follow_up_date:
                        apt.follow_up_date = consult.follow_up_date
                    apt.save()

            consult.save()

            # Create PatientDisease if a disease was selected
            disease = form.cleaned_data.get('disease_catalog')
            if disease:
                if not PatientDisease.objects.filter(
                    patient=patient, disease=disease, is_active=True
                ).exists():
                    PatientDisease.objects.create(
                        patient=patient,
                        disease=disease,
                        diagnosed_date=timezone.now().date(),
                        is_active=True,
                    )

            messages.success(request, "Consultation record saved successfully.")
            return redirect('doctor_patient_detail', patient_id=patient.patient_id)
    else:
        form = ConsultationForm()

    appointments = Appointment.objects.filter(
        doctor=doctor, patient=patient, status='APPROVED'
    )

    import json
    return render(request, "doctor/add_consultation.html", {
        "doctor": doctor,
        "patient": patient,
        "form": form,
        "appointments": appointments,
        "diseases_json": json.dumps(diseases_json),
        "preselected_apt_id": preselected_apt_id,
    })


# ── Hospital Affiliations (doctor-side) ───────────────────────────────────────

def hospital_affiliations(request):
    doctor = get_session_doctor(request)
    if not doctor:
        return redirect("doctor_login")

    if request.method == "POST":
        hosp_id = request.POST.get('hospital_id')
        hospital = get_object_or_404(Hospital, id=hosp_id)

        affil, created = HospitalAffiliation.objects.get_or_create(
            doctor=doctor, hospital=hospital
        )
        if not created and affil.status == 'REJECTED':
            affil.status = 'PENDING'
            affil.requested_at = timezone.now()
            affil.save()
            messages.success(request, f"Re-requested affiliation with {hospital.name}.")
        elif created:
            messages.success(request, f"Affiliation requested with {hospital.name}.")
        else:
            messages.info(request, f"Affiliation with {hospital.name} is already {affil.status}.")

        return redirect('doctor_hospital_affiliations')

    affiliations = HospitalAffiliation.objects.filter(doctor=doctor).select_related('hospital')
    linked_hosp_ids = affiliations.values_list('hospital_id', flat=True)
    available_hospitals = Hospital.objects.exclude(id__in=linked_hosp_ids)

    return render(request, "doctor/hospital_affiliations.html", {
        "doctor": doctor,
        "affiliations": affiliations,
        "available_hospitals": available_hospitals,
    })


# ── Disease Catalog Management ──────────────────────────────────────────────────

def doctor_disease_catalog(request):
    doctor = get_session_doctor(request)
    if not doctor:
        return redirect("doctor_login")
        
    from patient.models import DiseaseCatalog
    
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == 'toggle_hereditary':
            disease_id = request.POST.get("disease_id")
            disease = DiseaseCatalog.objects.filter(id=disease_id).first()
            if disease:
                disease.is_hereditary = not disease.is_hereditary
                disease.save()
                status = "hereditary" if disease.is_hereditary else "non-hereditary"
                messages.success(request, f"Marked {disease.name} as {status}.")
                
        elif action == 'add_disease':
            name = request.POST.get("disease_name", "").strip()
            icd_code = request.POST.get("icd_code", "").strip()
            is_hereditary = request.POST.get("is_hereditary") == "on"
            
            if name:
                if not DiseaseCatalog.objects.filter(name__iexact=name).exists():
                    DiseaseCatalog.objects.create(
                        name=name,
                        icd_code=icd_code if icd_code else None,
                        is_hereditary=is_hereditary
                    )
                    messages.success(request, f"Added {name} to the system disease catalog.")
                else:
                    messages.error(request, f"Disease '{name}' already exists in the catalog.")
            else:
                messages.error(request, "Disease name is required.")
                
        elif action == 'flag_patient':
            disease_id = request.POST.get("disease_id")
            patient_id = request.POST.get("patient_id", "").strip()
            
            disease = DiseaseCatalog.objects.filter(id=disease_id).first()
            from patient.models import Patient, PatientDisease, DoctorAccessLog, Appointment
            patient = Patient.objects.filter(patient_id=patient_id).first()
            
            if disease and patient:
                has_access = DoctorAccessLog.objects.filter(doctor=doctor, patient=patient).exists()
                has_apt = Appointment.objects.filter(doctor=doctor, patient=patient, status__in=['APPROVED', 'COMPLETED']).exists()
                
                if not (has_access or has_apt):
                    messages.error(request, "You are not authorized to flag this patient.")
                else:
                    pd, created = PatientDisease.objects.get_or_create(
                        patient=patient,
                        disease=disease,
                        defaults={'diagnosed_date': timezone.now().date(), 'is_active': True}
                    )
                    if created:
                        messages.success(request, f"Successfully flagged {patient.user.get_full_name() or patient.patient_id} with {disease.name}.")
                    else:
                        if not pd.is_active:
                            pd.is_active = True
                            pd.diagnosed_date = timezone.now().date()
                            pd.save()
                            messages.success(request, f"Re-activated {disease.name} for {patient.user.get_full_name() or patient.patient_id}.")
                        else:
                            messages.info(request, f"Patient is already flagged with {disease.name}.")
            else:
                messages.error(request, "Invalid Disease or Personal Health ID.")
                
        return redirect('doctor_disease_catalog')
        
    diseases = DiseaseCatalog.objects.all().order_by('name')
    
    return render(request, "doctor/disease_catalog.html", {
        "doctor": doctor,
        "diseases": diseases,
    })