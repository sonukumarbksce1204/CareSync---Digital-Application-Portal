from django.contrib import admin
from django.utils import timezone
from .models import Doctor, Specialization, Qualification, DoctorVerification


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'verification_status', 'profile_status')
    search_fields = ('full_name', 'email')
    list_filter = ('verification_status', 'profile_status')
    actions = ['approve_doctors', 'reject_doctors']

    @admin.action(description='Approve selected doctors')
    def approve_doctors(self, request, queryset):
        for doctor in queryset:
            doctor.verification_status = 'verified'
            doctor.save(update_fields=['verification_status'])
            if hasattr(doctor, 'verification'):
                doctor.verification.verified_by_admin = True
                doctor.verification.verified_at = timezone.now()
                doctor.verification.save()
        self.message_user(request, "Selected doctors have been approved.")

    @admin.action(description='Reject selected doctors')
    def reject_doctors(self, request, queryset):
        for doctor in queryset:
            doctor.verification_status = 'rejected'
            doctor.save(update_fields=['verification_status'])
            if hasattr(doctor, 'verification'):
                doctor.verification.verified_by_admin = False
                doctor.verification.verified_at = None
                doctor.verification.save()
        self.message_user(request, "Selected doctors have been rejected.")


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