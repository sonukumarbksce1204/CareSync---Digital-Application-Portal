from django.shortcuts import render, redirect
from .forms import HospitalForm
from .models import Hospital, HospitalImage
from django.contrib.auth.hashers import check_password
from django.contrib import messages

def hospital_register(request):
    if request.method == 'POST':
        form = HospitalForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('hospital_success')  # or any success page you have
    else:
        form = HospitalForm()
    return render(request, 'hospital/hospital_register.html', {'form': form})

def hospital_success(request):
    return render(request, 'hospital/hospital_success.html')


def hospital_login(request):
    if request.method == "POST":
        reg_no = request.POST.get("registration_number")
        password = request.POST.get("password")

        try:
            hospital = Hospital.objects.get(registration_number=reg_no)
            if check_password(password, hospital.password):
                # Login successful
                request.session['hospital_id'] = hospital.id  # store in session
                messages.success(request, f"Welcome {hospital.name}!")
                return redirect('hospital_dashboard')  # replace with your dashboard
            else:
                messages.error(request, "Invalid password.")
        except Hospital.DoesNotExist:
            messages.error(request, "Hospital with this registration number does not exist.")

    return render(request, "hospital/hospital_login.html")

def get_session_hospital(request):
    hospital_id = request.session.get("hospital_id")
    if not hospital_id: return None
    return Hospital.objects.filter(id=hospital_id).first()

#  Dashboard View for the hospital
def hospital_dashboard(request):
    hospital = get_session_hospital(request)
    if not hospital:
        request.session.flush()
        return redirect("hospital_login")

    # Upload image
    if request.method == "POST" and request.FILES.get("image"):
        HospitalImage.objects.create(
            hospital=hospital,
            image=request.FILES["image"]
        )
        return redirect("hospital_dashboard")

    images = hospital.images.all()

    return render(request, "hospital/hospital_dashboard.html", {
        "hospital": hospital,
        "images": images
    })


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
                return render(request, 'hospital/family_result.html', {'family': family, 'summary': summary, 'hospital': hospital})
                
        elif search_type == 'personal':
            patient = Patient.objects.filter(patient_id=query).first()
            if patient:
                log_hospital_access(hospital, 'PERSONAL', patient=patient)
                
                if request.GET.get('expand') == 'true' and patient.family:
                    log_hospital_access(hospital, 'EXPANDED', patient=patient, family=patient.family)
                    summary = get_family_disease_summary(patient.family)
                    return render(request, 'hospital/family_result.html', {'family': patient.family, 'summary': summary, 'hospital': hospital})
                
                return redirect('hospital_patient_detail', patient_id=patient.patient_id)

        from django.contrib import messages
        if search_type == 'personal':
            messages.error(request, "Personal Health ID not found. Please verify the 4-character ID.")
        elif search_type == 'family':
            messages.error(request, "Family Health ID not found. Please verify the 6-digit code.")
        else:
            messages.error(request, "Invalid search type. Please select Personal ID or Family ID.")
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
    return render(request, 'hospital/patient_result.html', {'patient': patient, 'hospital': hospital})