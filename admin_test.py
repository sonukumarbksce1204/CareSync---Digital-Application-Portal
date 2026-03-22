import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CareSync.settings')
import django
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from doctor.models import DoctorVerification, Doctor

# Get or create superuser
admin, _ = User.objects.get_or_create(username='admin_test', is_superuser=True, is_staff=True)
admin.set_password('admin_test')
admin.save()

client = Client()
client.login(username='admin_test', password='admin_test')

dv = DoctorVerification.objects.get(license_number='4325')
doc = dv.doctor
print(f"Before: verified_by_admin={dv.verified_by_admin}, status={doc.verification_status}")

# Try to toggle it to False if True, or True if False
new_admin_verified = not dv.verified_by_admin

url = f'/admin/doctor/doctorverification/{dv.id}/change/'
response = client.get(url)
print(f"GET form context status: {response.status_code}")

post_data = {
    'doctor': str(doc.id),
    'verified_by_admin': 'on' if new_admin_verified else '',
    '_save': 'Save'
}

response = client.post(url, post_data, follow=True)
print(f"POST response: {response.status_code}")

dv.refresh_from_db()
doc.refresh_from_db()
print(f"After POST: verified_by_admin={dv.verified_by_admin}, status={doc.verification_status}")
