from django import forms
from django.contrib.auth.models import User
from .models import Patient, Symptom, Appointment
from doctor.models import Doctor
from hospital.models import Hospital
from django.utils import timezone

# ==============================
# USER SIGNUP FORM
# ==============================
class PatientSignUpForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "input-field",
            "placeholder": "Enter password"
        })
    )

    class Meta:
        model = User
        fields = ["username", "email", "password"]
        help_texts = {"username": ""}
        widgets = {
            "username": forms.TextInput(attrs={
                "class": "input-field",
                "placeholder": "Enter username"
            }),
            "email": forms.EmailInput(attrs={
                "class": "input-field",
                "placeholder": "Enter email"
            }),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


# ==============================
# PATIENT PROFILE FORM
# ==============================
class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            "age",
            "gender",
            "blood_group",
            "phone",
            "address",
            "emergency_contact",
        ]
        widgets = {
            "age": forms.NumberInput(attrs={
                "class": "input-field",
                "placeholder": "Enter age"
            }),
            "phone": forms.TextInput(attrs={
                "class": "input-field",
                "placeholder": "Enter phone number"
            }),
            "address": forms.Textarea(attrs={
                "class": "input-field",
                "placeholder": "Enter address",
                "rows": 3
            }),
        }


# ==============================
# SYMPTOM FORM (ML-SAFE)
# ==============================
class SymptomForm(forms.ModelForm):
    """
    IMPORTANT:
    - `selected_symptoms` is NOT a model field
    - It is validated against symptom_index.pkl
    - Only this field is used for ML prediction
    """

    selected_symptoms = forms.MultipleChoiceField(
        required=False,
        choices=[],
        widget=forms.SelectMultiple(attrs={
            "class": "input-field",
        }),
        help_text="Select symptoms from the list only",
    )

    class Meta:
        model = Symptom
        fields = [
            "description",
            "address",
            "duration_days",
            "medicines_taken",
            "improvement",
            "image",
            "test_report",
        ]

        widgets = {
            "description": forms.Textarea(attrs={
                "class": "input-field",
                "placeholder": "Describe your symptoms (for doctor reference only)",
                "rows": 4
            }),
            "address": forms.TextInput(attrs={
                "class": "input-field",
                "placeholder": "Enter current address"
            }),
            "duration_days": forms.NumberInput(attrs={
                "class": "input-field",
                "placeholder": "How many days since it started?"
            }),
            "medicines_taken": forms.Textarea(attrs={
                "class": "input-field",
                "placeholder": "Mention any medicines already taken",
                "rows": 3
            }),
            "improvement": forms.Select(attrs={
                "class": "input-field"
            }),
            "image": forms.ClearableFileInput(attrs={
                "class": "input-field"
            }),
            "test_report": forms.ClearableFileInput(attrs={
                "class": "input-field"
            }),
        }

    def __init__(self, *args, **kwargs):
        """
        Dynamically load symptoms from ML predictor
        (NO TensorFlow required)
        """
        super().__init__(*args, **kwargs)

        try:
            from ml_model import predictor
            symptoms = predictor.get_symptom_list()
            self.fields["selected_symptoms"].choices = [
                (s, s.replace("_", " ").title()) for s in symptoms
            ]
        except Exception:
            self.fields["selected_symptoms"].choices = []

    def clean_selected_symptoms(self):
        """
        SECURITY:
        Prevents POST tampering with invalid symptom names
        """
        selected = self.cleaned_data.get("selected_symptoms", [])

        try:
            from ml_model import predictor
            valid = set(predictor.get_symptom_list())
        except Exception:
            valid = set()

        invalid = [s for s in selected if s not in valid]
        if invalid:
            raise forms.ValidationError(
                f"Invalid symptoms detected: {', '.join(invalid)}"
            )
        return selected


# ==============================
# FAMILY HEAD CHANGE FORM
# ==============================
class ChangeFamilyHeadForm(forms.Form):
    new_head = forms.ModelChoiceField(queryset=Patient.objects.none(), empty_label="Select New Head")
    reason = forms.CharField(widget=forms.Textarea(attrs={
        "class": "input-field", "placeholder": "Reason for transfer", "rows": 3
    }), required=True)

    def __init__(self, *args, **kwargs):
        family = kwargs.pop('family', None)
        super().__init__(*args, **kwargs)
        if family:
            self.fields['new_head'].queryset = Patient.objects.filter(family=family, is_deceased=False).exclude(id=family.head.id)
        self.fields['new_head'].widget.attrs.update({'class': 'input-field'})


# ==============================
# FAMILY JOIN REQUEST FORM
# ==============================
class RequestJoinFamilyForm(forms.Form):
    family_id = forms.CharField(max_length=6, widget=forms.TextInput(attrs={
        "class": "input-field", "placeholder": "Enter 6-digit Family ID"
    }))
    relationship = forms.ChoiceField(
        choices=[
            ('SPOUSE', 'Spouse'), ('SON', 'Son'), ('DAUGHTER', 'Daughter'),
            ('FATHER', 'Father'), ('MOTHER', 'Mother'), ('BROTHER', 'Brother'), ('SISTER', 'Sister'),
            ('GRANDFATHER', 'Grandfather'), ('GRANDMOTHER', 'Grandmother'),
            ('GUARDIAN', 'Guardian'), ('OTHER', 'Other')
        ], 
        widget=forms.Select(attrs={"class": "input-field", "id": "id_relationship"})
    )
    custom_relationship = forms.CharField(
        max_length=50, required=False, 
        widget=forms.TextInput(attrs={"class": "input-field", "placeholder": "Please specify relationship", "id": "id_custom_relationship"})
    )

    def clean_family_id(self):
        family_id = self.cleaned_data.get('family_id')
        from patient.models import Family
        if not Family.objects.filter(family_id=family_id).exists():
            raise forms.ValidationError("Invalid Family ID")
        return family_id

    def clean(self):
        cleaned_data = super().clean()
        relationship = cleaned_data.get('relationship')
        custom_relationship = cleaned_data.get('custom_relationship')

        if relationship == 'OTHER' and not custom_relationship:
            self.add_error('custom_relationship', "Please specify your relationship if selecting 'Other'.")

        return cleaned_data

# ==============================
# APPOINTMENT FORM
# ==============================
class AppointmentForm(forms.ModelForm):
    doctor = forms.ModelChoiceField(queryset=Doctor.objects.filter(verification_status='verified'), required=False, empty_label="Select Doctor (Optional)")
    hospital = forms.ModelChoiceField(queryset=Hospital.objects.all(), required=False, empty_label="Select Hospital (Optional)")
    
    class Meta:
        model = Appointment
        fields = ['doctor', 'hospital', 'preferred_date', 'reason', 'note']
        widgets = {
            'preferred_date': forms.DateInput(attrs={'type': 'date', 'class': 'input-field'}),
            'reason': forms.Textarea(attrs={'rows': 3, 'class': 'input-field', 'placeholder': 'Symptoms or reason...'}),
            'note': forms.Textarea(attrs={'rows': 2, 'class': 'input-field', 'placeholder': 'Optional instructions...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        doctor = cleaned_data.get('doctor')
        hospital = cleaned_data.get('hospital')
        pref_date = cleaned_data.get('preferred_date')

        if (not doctor and not hospital) or (doctor and hospital):
            raise forms.ValidationError("You must select exactly one: either a Doctor OR a Hospital.")
            
        if pref_date and pref_date < timezone.now().date():
            raise forms.ValidationError("Preferred date cannot be in the past.")

        return cleaned_data

# ==============================
# PATIENT PROFILE UPDATE FORM
# ==============================
class PatientProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['age', 'gender', 'blood_group', 'phone', 'emergency_contact', 'address']
        widgets = {
            'age': forms.NumberInput(attrs={'class': 'input-field'}),
            'gender': forms.Select(attrs={'class': 'input-field'}),
            'blood_group': forms.TextInput(attrs={'class': 'input-field'}),
            'phone': forms.TextInput(attrs={'class': 'input-field'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'input-field'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'input-field'}),
        }