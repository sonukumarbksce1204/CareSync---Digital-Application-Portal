from django import forms
from .models import Doctor


class DoctorSignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Doctor
        fields = ['full_name', 'email', 'phone', 'experience_years', 'specializations', 'password']

    def save(self, commit=True):
        doctor = super().save(commit=False)
        doctor.set_password(self.cleaned_data['password'])   # ⭐ hashing here
        if commit:
            doctor.save()
            self.save_m2m()
        return doctor


class DoctorLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

from patient.models import Symptom

class AIReviewForm(forms.ModelForm):
    class Meta:
        model = Symptom
        fields = ['ai_prediction_status', 'doctor_modified_diagnosis_text', 'doctor_diagnosis_notes', 'verification_note']
        widgets = {
            'verification_note': forms.Textarea(attrs={'rows': 3, 'class': 'input-field'}),
            'doctor_diagnosis_notes': forms.TextInput(attrs={'class': 'input-field'}),
            'ai_prediction_status': forms.Select(attrs={'class': 'input-field'}),
            'doctor_modified_diagnosis_text': forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Enter final disease diagnosis...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('ai_prediction_status')
        modified_text = cleaned_data.get('doctor_modified_diagnosis_text')
        notes = cleaned_data.get('doctor_diagnosis_notes')
        v_note = cleaned_data.get('verification_note')

        if status == 'MODIFIED' and not modified_text:
            raise forms.ValidationError("If modified, a final diagnosis text must be provided.")
        if status in ['MODIFIED', 'REJECTED'] and not v_note:
            raise forms.ValidationError("A verification note is required when modifying or rejecting.")
            
        return cleaned_data

from patient.models import ConsultationRecord, DiseaseCatalog

class ConsultationForm(forms.ModelForm):
    disease_catalog = forms.ModelChoiceField(
        queryset=DiseaseCatalog.objects.all(),
        required=False,
        label="Diagnose Disease (Optional)",
        widget=forms.Select(attrs={'class': 'input-field', 'style': 'width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px;'})
    )

    class Meta:
        model = ConsultationRecord
        fields = ['diagnosis_text', 'notes', 'doctor_instructions', 'follow_up_date', 'prescription_document']
        widgets = {
            'diagnosis_text': forms.TextInput(attrs={'class': 'input-field', 'style': 'width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px;', 'placeholder': 'Type exact medical diagnosis...'}),
            'notes': forms.Textarea(attrs={'rows': 4, 'class': 'input-field', 'placeholder': 'Enter clinical notes here...', 'style': 'width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px;'}),
            'doctor_instructions': forms.Textarea(attrs={'rows': 3, 'class': 'input-field', 'placeholder': 'Instructions for the patient...', 'style': 'width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px;'}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date', 'class': 'input-field', 'style': 'width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px;'}),
            'prescription_document': forms.FileInput(attrs={'class': 'input-field', 'style': 'width: 100%; padding: 10px;'}),
        }

class DoctorProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['phone', 'experience_years', 'profile_image']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'input-field', 'style': 'width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px;'}),
            'experience_years': forms.NumberInput(attrs={'class': 'input-field', 'style': 'width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 5px;'}),
            'profile_image': forms.FileInput(attrs={'class': 'input-field', 'style': 'width: 100%; padding: 10px;'}),
        }