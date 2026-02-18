from django import forms
from django.contrib.auth.models import User
from .models import Patient, Symptom


# ==============================
# USER SIGNUP FORM
# ==============================
class PatientSignUpForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'input-field',
            'placeholder': 'Enter password'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        help_texts = {
            'username': ''
        }
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'Enter username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input-field',
                'placeholder': 'Enter email'
            }),
        }

    # Secure password hashing
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
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
            'age',
            'gender',
            'blood_group',
            'phone',
            'address',
            'emergency_contact'
        ]
        widgets = {
            'age': forms.NumberInput(attrs={
                'class': 'input-field',
                'placeholder': 'Enter age'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'Enter phone number'
            }),
            'address': forms.Textarea(attrs={
                'class': 'input-field',
                'placeholder': 'Enter address',
                'rows': 3
            }),
        }


# ==============================
# UPDATED SYMPTOM FORM
# ==============================
class SymptomForm(forms.ModelForm):
    class Meta:
        model = Symptom
        fields = [
            'description',
            'address',
            'duration_days',
            'medicines_taken',
            'improvement',
            'image',
            'test_report'
        ]

        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'input-field',
                'placeholder': 'Describe your symptoms...',
                'rows': 4
            }),

            'address': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'Enter current address'
            }),

            'duration_days': forms.NumberInput(attrs={
                'class': 'input-field',
                'placeholder': 'How many days since it started?'
            }),

            'medicines_taken': forms.Textarea(attrs={
                'class': 'input-field',
                'placeholder': 'Mention any medicines already taken',
                'rows': 3
            }),

            'improvement': forms.Select(attrs={
                'class': 'input-field'
            }),

            'image': forms.ClearableFileInput(attrs={
                'class': 'input-field'
            }),

            'test_report': forms.ClearableFileInput(attrs={
                'class': 'input-field'
            }),
        }
