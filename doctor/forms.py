from django import forms
from .models import Doctor
from patient.models import Symptom, DiseaseCatalog, ConsultationRecord


# Consultation type choices must be defined at module level
CONSULTATION_TYPE_CHOICES = [
    ('', '-- Select visit type --'),
    ('FIRST_VISIT', 'First Visit'),
    ('FOLLOW_UP', 'Follow-up'),
    ('ROUTINE', 'Routine Check'),
    ('EMERGENCY', 'Emergency'),
]


# ── Doctor Signup / Profile ───────────────────────────────────────────────────


class DoctorSignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Doctor
        fields = ['full_name', 'email', 'phone', 'experience_years', 'specializations', 'password']

    def save(self, commit=True):
        doctor = super().save(commit=False)
        doctor.set_password(self.cleaned_data['password'])
        if commit:
            doctor.save()
            self.save_m2m()
        return doctor


class DoctorLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)


class DoctorProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['phone', 'experience_years', 'profile_image']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'input-field', 'style': 'width:100%;padding:10px;border:1px solid #ccc;border-radius:5px;'}),
            'experience_years': forms.NumberInput(attrs={'class': 'input-field', 'style': 'width:100%;padding:10px;border:1px solid #ccc;border-radius:5px;'}),
            'profile_image': forms.FileInput(attrs={'class': 'input-field', 'style': 'width:100%;padding:10px;'}),
        }


# ── AI Review Form ────────────────────────────────────────────────────────────


class AIReviewForm(forms.ModelForm):
    """
    Used by doctors to verify AI predictions on patient symptom records.
    doctor_final_diagnosis_catalog is shown/required when status is MODIFIED.
    """
    doctor_final_diagnosis_catalog = forms.ModelChoiceField(
        queryset=DiseaseCatalog.objects.all(),
        required=False,
        label="Final Diagnosis (Disease Catalog)",
        empty_label="-- Select disease from catalog (optional) --",
        widget=forms.Select(attrs={'class': 'input-field', 'id': 'id_doctor_final_diagnosis_catalog'}),
        help_text="Select the correct disease from the catalog if modifying the AI diagnosis."
    )

    class Meta:
        model = Symptom
        fields = [
            'ai_prediction_status',
            'doctor_final_diagnosis_catalog',
            'doctor_modified_diagnosis_text',
            'doctor_diagnosis_notes',
            'verification_note',
        ]
        widgets = {
            'ai_prediction_status': forms.Select(attrs={'class': 'input-field', 'id': 'id_ai_prediction_status'}),
            'doctor_modified_diagnosis_text': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'Enter free-text final diagnosis (if not in catalog)...',
            }),
            'doctor_diagnosis_notes': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'Clinical reasoning or additional notes...',
            }),
            'verification_note': forms.Textarea(attrs={
                'rows': 3,
                'class': 'input-field',
                'placeholder': 'Internal verification note for audit trail...',
            }),
        }

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get('ai_prediction_status')
        catalog = cleaned.get('doctor_final_diagnosis_catalog')
        modified_text = cleaned.get('doctor_modified_diagnosis_text')
        v_note = cleaned.get('verification_note')

        if status == 'MODIFIED':
            if not catalog and not modified_text:
                raise forms.ValidationError(
                    "When modifying, provide either a catalog diagnosis or a free-text final diagnosis."
                )

        if status in ['MODIFIED', 'REJECTED'] and not v_note:
            raise forms.ValidationError(
                "A verification note is required when modifying or rejecting an AI prediction."
            )

        return cleaned


# ── Consultation Form ─────────────────────────────────────────────────────────


_INPUT = 'width:100%;padding:10px;border:1px solid #ccc;border-radius:5px;'

CONSULTATION_TYPE_CHOICES = [
    ('', '-- Select visit type --'),
    ('FIRST_VISIT', 'First Visit'),
    ('FOLLOW_UP', 'Follow-up'),
    ('ROUTINE', 'Routine Check'),
    ('EMERGENCY', 'Emergency'),
]

class ConsultationForm(forms.ModelForm):
    """
    Clinical note form used by doctors when recording a consultation.
    disease_catalog is a non-model field handled manually in the view.
    """
    disease_catalog = forms.ModelChoiceField(
        queryset=DiseaseCatalog.objects.all(),
        required=False,
        label="Diagnose Disease (Optional)",
        empty_label="-- No specific disease diagnosis --",
        widget=forms.Select(attrs={'class': 'input-field', 'style': _INPUT, 'id': 'id_disease_catalog'}),
        help_text="Selecting a hereditary disease will flag a caution notice."
    )

    class Meta:
        model = ConsultationRecord
        fields = [
            'diagnosis_text',
            'notes',
            'doctor_instructions',
            'follow_up_date',
            'follow_up_note',
            'consultation_type',
            'prescription_document',
            'visible_to_patient',
        ]
        widgets = {
            'diagnosis_text': forms.TextInput(attrs={
                'class': 'input-field', 'style': _INPUT,
                'placeholder': 'Type exact medical diagnosis text...',
            }),
            'notes': forms.Textarea(attrs={
                'rows': 4, 'class': 'input-field',
                'placeholder': 'Clinical observations, examination findings...',
                'style': _INPUT,
            }),
            'doctor_instructions': forms.Textarea(attrs={
                'rows': 3, 'class': 'input-field',
                'placeholder': 'Patient-facing instructions (diet, medication, rest)...',
                'style': _INPUT,
            }),
            'follow_up_date': forms.DateInput(attrs={
                'type': 'date', 'class': 'input-field', 'style': _INPUT,
            }),
            'follow_up_note': forms.Textarea(attrs={
                'rows': 2, 'class': 'input-field',
                'placeholder': 'What to monitor or address at follow-up...',
                'style': _INPUT,
            }),
            'consultation_type': forms.Select(attrs={
                'class': 'input-field',
                'style': _INPUT,
            }),
            'prescription_document': forms.FileInput(attrs={
                'class': 'input-field', 'style': 'width:100%;padding:10px;',
            }),
            'visible_to_patient': forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['consultation_type'].choices = CONSULTATION_TYPE_CHOICES
