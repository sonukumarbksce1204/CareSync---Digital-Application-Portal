import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CareSync.settings')
import django
django.setup()

from django.contrib import admin
from doctor.models import Doctor, DoctorVerification
from doctor.admin import DoctorVerificationAdmin

d = Doctor.objects.get(full_name='Dr.Chandel')
v = d.verification
print(f"Before: v_admin={v.verified_by_admin}, status={d.verification_status}")

# Simulate Admin save
admin_instance = DoctorVerificationAdmin(DoctorVerification, admin.site)
admin_instance.save_model(None, v, None, True)

d.refresh_from_db()
print(f"After: v_admin={v.verified_by_admin}, status={d.verification_status}")
