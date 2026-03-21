from django import forms
from django.contrib.auth.models import User
from .models import Patient, Symptom


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