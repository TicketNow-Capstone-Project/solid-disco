from django import forms
from django.core.validators import RegexValidator
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser


def validate_phone_number(value):
    """Consolidated phone number validation."""
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+639171234567'. Up to 15 digits allowed."
    )
    phone_regex(value)


def validate_zip_code(value):
    """Consolidated ZIP code validation."""
    zip_regex = RegexValidator(
        regex='^[0-9]{4}$', 
        message='Enter a valid 4-digit ZIP code'
    )
    zip_regex(value)


class BaseFormMixin:
    """Mixin to apply consistent form styling."""
    
    def apply_bootstrap_classes(self):
        """Apply Bootstrap classes to form fields."""
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            elif isinstance(field.widget, forms.TextInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.EmailInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({'class': 'form-control'})
            elif isinstance(field.widget, forms.PasswordInput):
                field.widget.attrs.update({'class': 'form-control'})


# ✅ DRIVER REGISTRATION FORM (with consolidated validation)
class DriverRegistrationForm(forms.Form, BaseFormMixin):
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'First Name'})
    )
    middle_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Middle Name'})
    )
    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Last Name'})
    )
    suffix = forms.ChoiceField(
        choices=[('', 'Select Suffix'), ('Jr.', 'Jr.'), ('Sr.', 'Sr.'), ('II', 'II'), ('III', 'III')],
        required=False
    )

    # Contact Information with consolidated validation
    mobile_number = forms.CharField(
        validators=[validate_phone_number],
        max_length=17,
        widget=forms.TextInput(attrs={
            'placeholder': '+639171234567',
            'pattern': '^(\\+63|0)9\\d{9}$'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'email@example.com'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()

    # Address
    house_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'House/Bldg No.'})
    )
    street = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street'})
    )
    barangay = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Barangay'})
    )
    city_municipality = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City/Municipality'})
    )
    province = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Province'})
    )
    zip_code = forms.CharField(
        max_length=4,
        validators=[RegexValidator(regex='^[0-9]{4}$', message='Enter a valid 4-digit ZIP code')],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ZIP Code', 'pattern': '[0-9]{4}'})
    )

    # License Information
    license_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'N01-23-456789'})
    )
    license_expiry = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    license_type = forms.ChoiceField(
        choices=[
            ('', 'Select License Type'),
            ('Student', 'Student Permit'),
            ('Non-Professional', 'Non-Professional'),
            ('Professional', 'Professional'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    # Additional Info
    birth_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    birth_place = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Place of Birth'})
    )
    blood_type = forms.ChoiceField(
        choices=[
            ('', 'Select Blood Type'),
            ('A+', 'A+'), ('A-', 'A-'),
            ('B+', 'B+'), ('B-', 'B-'),
            ('AB+', 'AB+'), ('AB-', 'AB-'),
            ('O+', 'O+'), ('O-', 'O-'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    # Emergency Contact
    emergency_contact_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emergency Contact Name'})
    )
    emergency_contact_number = forms.CharField(
        validators=[phone_regex],
        max_length=17,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+639171234567',
            'pattern': '^(\\+63|0)9\\d{9}$'
        })
    )
    emergency_contact_relationship = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Relationship'})
    )


# ✅ UPDATED ROLE-AWARE CUSTOM USER CREATION FORM (Admin + Staff)
class CustomUserCreationForm(UserCreationForm):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('staff_admin', 'Staff Admin'),
    ]
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        label="Account Role",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'}),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}),
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        """Hide the Admin role if a staff_admin is creating a user."""
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # 🎨 Apply Bootstrap classes for UI update
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username'
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Email Address'
        })
        self.fields['role'].widget.attrs.update({
            'class': 'form-select'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control'
        })

        # Restrict role if staff_admin is creating the account
        if user and getattr(user, 'role', '') == 'staff_admin':
            self.fields['role'].choices = [('staff_admin', 'Staff Admin')]

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data.get('role')

        # Assign correct privileges
        if role == 'admin':
            user.is_staff = True
            user.is_superuser = True
        elif role == 'staff_admin':
            user.is_staff = True
            user.is_superuser = False
        else:
            user.is_staff = False
            user.is_superuser = False

        if commit:
            user.save()
        return user



# ✅ USER EDIT FORM
class CustomUserEditForm(UserChangeForm):
    password = None  # hide the default password field

    new_password1 = forms.CharField(
        label="New Password",
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        })
    )

    new_password2 = forms.CharField(
        label="Confirm New Password",
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role']

        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address'
            }),
            'role': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        p1 = cleaned_data.get("new_password1")
        p2 = cleaned_data.get("new_password2")

        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError("Passwords do not match.")

            if len(p1) < 6:
                raise forms.ValidationError(
                    "Password must be at least 6 characters long."
                )

        return cleaned_data
