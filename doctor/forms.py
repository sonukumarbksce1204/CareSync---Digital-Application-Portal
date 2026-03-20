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