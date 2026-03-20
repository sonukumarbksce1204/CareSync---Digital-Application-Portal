from django.contrib import admin
from .models import Doctor, Specialization, Qualification, DoctorVerification


class DoctorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'verification_status')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.set_password(obj.password)
        super().save_model(request, obj, form, change)


class DoctorVerificationAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'license_number', 'verified_by_admin')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if obj.verified_by_admin:
            doctor = obj.doctor
            doctor.verification_status = 'verified'
            doctor.save()


admin.site.register(Doctor, DoctorAdmin)
admin.site.register(Specialization)
admin.site.register(Qualification)
admin.site.register(DoctorVerification, DoctorVerificationAdmin)