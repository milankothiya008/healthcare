from django import forms
from django.contrib.auth import get_user_model
from .models import PatientProfile

User = get_user_model()


class PatientProfileForm(forms.ModelForm):
    """Form for editing patient profile"""
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    phone_number = forms.CharField(max_length=15, required=False)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)

    class Meta:
        model = PatientProfile
        fields = [
            'profile_picture', 'date_of_birth', 'gender', 'blood_group',
            'emergency_contact_name', 'emergency_contact_phone',
            'medical_history', 'allergies'
        ]
        widgets = {
            'medical_history': forms.Textarea(attrs={'rows': 4}),
            'allergies': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['phone_number'].initial = self.instance.user.phone_number
            self.fields['address'].initial = self.instance.user.address
        for field in self.fields:
            if hasattr(self.fields[field], 'widget') and 'class' not in self.fields[field].widget.attrs:
                self.fields[field].widget.attrs['class'] = 'form-control'

    def save(self, commit=True):
        profile = super().save(commit=False)
        if profile.user:
            profile.user.first_name = self.cleaned_data.get('first_name', '')
            profile.user.last_name = self.cleaned_data.get('last_name', '')
            profile.user.phone_number = self.cleaned_data.get('phone_number', '')
            profile.user.address = self.cleaned_data.get('address', '')
            if self.files.get('profile_picture'):
                profile.user.profile_picture = self.files['profile_picture']
            profile.user.save()
        if commit:
            profile.save()
        return profile
