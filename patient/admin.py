from django.contrib import admin
from .models import Family, Patient, Symptom, DiseaseCatalog, PatientDisease, DoctorAccessLog, FamilyHeadChangeLog, FamilyJoinRequest

@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ('family_id', 'head', 'created_at')
    search_fields = ('family_id', 'head__user__username')

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('patient_id', 'user', 'family', 'family_relationship', 'is_deceased')
    search_fields = ('patient_id', 'user__username', 'phone')
    list_filter = ('family_relationship', 'is_deceased')

@admin.register(Symptom)
class SymptomAdmin(admin.ModelAdmin):
    list_display = ('patient', 'predicted_disease', 'created_at')

@admin.register(DiseaseCatalog)
class DiseaseCatalogAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_hereditary', 'icd_code')
    list_filter = ('is_hereditary',)

@admin.register(PatientDisease)
class PatientDiseaseAdmin(admin.ModelAdmin):
    list_display = ('patient', 'disease', 'is_active', 'diagnosed_date')
    list_filter = ('is_active', 'disease__is_hereditary')

@admin.register(DoctorAccessLog)
class DoctorAccessLogAdmin(admin.ModelAdmin):
    list_display = ('doctor', 'access_method', 'patient', 'family', 'accessed_at')
    list_filter = ('access_method', 'accessed_at')

@admin.register(FamilyHeadChangeLog)
class FamilyHeadChangeLogAdmin(admin.ModelAdmin):
    list_display = ('family', 'old_head', 'new_head', 'changed_by', 'created_at')

@admin.register(FamilyJoinRequest)
class FamilyJoinRequestAdmin(admin.ModelAdmin):
    list_display = ('patient', 'family', 'requested_relationship', 'status', 'requested_at')
    list_filter = ('status', 'requested_relationship')
    search_fields = ('patient__user__username', 'family__family_id')

