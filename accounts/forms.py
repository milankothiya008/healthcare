from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
from doctors.models import DoctorProfile, DoctorProfileUpdateRequest


class UserRegistrationForm(UserCreationForm):
    """Custom registration form with role selection"""
    
    ROLE_CHOICES = [
        ('', 'Select Role'),
        ('DOCTOR', 'Doctor'),
        ('PATIENT', 'Patient'),
        ('HOSPITAL', 'Hospital'),
    ]
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone Number'
        })
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Address (optional)'
        })
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    verification_document = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png'
        }),
        help_text="Required for Doctors and Hospitals. Upload license/certificate document."
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'role', 'address', 'profile_picture', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })
    
    def clean_role(self):
        role = self.cleaned_data.get('role')
        if not role:
            raise forms.ValidationError("Please select a role.")
        if role == 'ADMIN':
            raise forms.ValidationError("Admin role cannot be selected during registration.")
        return role
    
    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        verification_doc = cleaned_data.get('verification_document')
        
        # Require verification document for Doctors and Hospitals
        if role in ['DOCTOR', 'HOSPITAL'] and not verification_doc:
            raise forms.ValidationError({
                'verification_document': 'Verification document is required for Doctors and Hospitals.'
            })
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone_number = self.cleaned_data['phone_number']
        user.role = self.cleaned_data['role']
        user.address = self.cleaned_data['address']
        
        # Doctors and Hospitals need approval
        if user.role in ['DOCTOR', 'HOSPITAL']:
            user.is_approved = False
        else:
            user.is_approved = True  # Patients are auto-approved
        
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    """Custom login form - login using email"""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )


class DoctorProfileEditForm(forms.Form):
    """Doctor profile: non-sensitive (save immediately) and sensitive (create update request)"""
    # Non-sensitive - applied immediately
    phone_number = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    profile_picture = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}))

    # Sensitive - create DoctorProfileUpdateRequest
    specialization = forms.ChoiceField(choices=DoctorProfile.SPECIALIZATION_CHOICES, required=False, widget=forms.Select(attrs={'class': 'form-control'}))
    qualification = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    license_number = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    verification_document = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png'}))

    def __init__(self, *args, user=None, doctor_profile=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.doctor_profile = doctor_profile
        if user:
            self.fields['phone_number'].initial = user.phone_number
            self.fields['address'].initial = user.address
        if doctor_profile:
            self.fields['specialization'].initial = doctor_profile.specialization
            self.fields['qualification'].initial = doctor_profile.qualification
            self.fields['license_number'].initial = doctor_profile.license_number

    def save_non_sensitive(self):
        if not self.user:
            return
        self.user.phone_number = self.cleaned_data.get('phone_number', '')
        self.user.address = self.cleaned_data.get('address', '')
        if self.cleaned_data.get('profile_picture'):
            self.user.profile_picture = self.cleaned_data['profile_picture']
        self.user.save(update_fields=['phone_number', 'address', 'profile_picture', 'updated_at'])
        if self.doctor_profile and self.cleaned_data.get('profile_picture'):
            self.doctor_profile.profile_picture = self.cleaned_data['profile_picture']
            self.doctor_profile.save(update_fields=['profile_picture', 'updated_at'])

    def create_update_requests(self):
        """Create PENDING DoctorProfileUpdateRequest for each changed sensitive field"""
        if not self.doctor_profile:
            return
        for field in ('specialization', 'qualification', 'license_number'):
            new_val = self.cleaned_data.get(field)
            if new_val is None:
                continue
            current = getattr(self.doctor_profile, field, None)
            if str(new_val) != str(current):
                DoctorProfileUpdateRequest.objects.create(
                    doctor=self.doctor_profile,
                    field_name=field,
                    new_value_text=str(new_val),
                    status='PENDING'
                )
        if self.cleaned_data.get('verification_document'):
            DoctorProfileUpdateRequest.objects.create(
                doctor=self.doctor_profile,
                field_name='verification_document',
                new_value_file=self.cleaned_data['verification_document'],
                status='PENDING'
            )
