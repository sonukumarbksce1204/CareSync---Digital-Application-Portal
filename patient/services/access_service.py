from patient.models import DoctorAccessLog

def can_view_patient(user, target_patient):
    """
    Guarantees siblings cannot view siblings.
    Only the exact patient, or the Family Head of their family, can view full medical records.
    """
    if not user.is_authenticated:
        return False
        
    # User is the patient
    if hasattr(user, 'patient') and user.patient == target_patient:
        return True
        
    # User is the family head
    if target_patient.family and target_patient.family.head and target_patient.family.head.user == user:
        return True
        
    return False

def can_manage_family(user, family):
    """
    Only the absolute Head can govern join requests and head-changes.
    """
    if not user.is_authenticated or not hasattr(user, 'patient'):
        return False
    return family.head == user.patient

def log_doctor_access(doctor, access_method, patient=None, family=None):
    """
    Audits doctor searches via Personal or Family ID streams.
    """
    return DoctorAccessLog.objects.create(
        doctor=doctor, 
        access_method=access_method, 
        patient=patient, 
        family=family
    )

def log_hospital_access(hospital, access_method, patient=None, family=None):
    """
    Audits hospital searches via Personal or Family ID streams.
    """
    from patient.models import HospitalAccessLog
    return HospitalAccessLog.objects.create(
        hospital=hospital, 
        access_method=access_method, 
        patient=patient, 
        family=family
    )
