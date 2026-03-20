from django.contrib import admin
from .models import Doctor, Specialization, Qualification, DoctorVerification


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'verification_status', 'profile_status')
    search_fields = ('full_name', 'email')
    list_filter = ('verification_status', 'profile_status')


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    search_fields = ('name',)


@admin.register(Qualification)
class QualificationAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'degree', 'institution')


@admin.register(DoctorVerification)
class DoctorVerificationAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'license_number', 'verified_by_admin', 'verified_at')

    readonly_fields = ('license_number', 'license_document')

    def has_add_permission(self, request):
        return False