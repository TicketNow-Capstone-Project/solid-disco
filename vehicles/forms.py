from django import forms
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date
import re
from .models import Driver, Vehicle, Deposit, Wallet, Route
from terminal.models import SystemSettings


# ✅ Placeholder for potential extended form
class FullVehicleDetailsForm(forms.Form):
    pass


# ======================================================
# VEHICLE REGISTRATION FORM
# ======================================================
import re
from datetime import date
from django import forms
from django.core.exceptions import ValidationError

from .models import Vehicle, Route, Driver


class VehicleRegistrationForm(forms.ModelForm):
    # All pattern validations removed

    class Meta:
        model = Vehicle
        fields = [
            'vehicle_name',
            'vehicle_type',
            'ownership_type',
            'assigned_driver',
            'route',
            'cr_number',
            'or_number',
            'vin_number',
            'year_model',
            'registration_number',
            'registration_expiry',
            'license_plate',
            'seat_capacity',
        ]
        widgets = {
            'registration_expiry': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set required fields
        required_fields = [
            'vehicle_type', 'ownership_type', 'assigned_driver', 
            'cr_number', 'or_number', 'vin_number', 'year_model',
            'registration_number', 'registration_expiry', 'license_plate'
        ]
        
        # Set all required fields
        for field_name in required_fields:
            self.fields[field_name].required = True
            
        # Set optional fields
        self.fields['vehicle_name'].required = False
        self.fields['route'].required = False
        self.fields['seat_capacity'].required = False
        
        # Add form-control class to all fields
        for field_name, field in self.fields.items():
            if 'class' in field.widget.attrs:
                field.widget.attrs['class'] += ' form-control'
            else:
                field.widget.attrs['class'] = 'form-control'
        self.fields['route'].queryset = Route.objects.filter(active=True)
        self.fields['assigned_driver'].queryset = Driver.objects.all()

    # --------------------------------------------------
    # SIMPLIFIED FIELD VALIDATION
    # --------------------------------------------------
    def clean_cr_number(self):
        value = self.cleaned_data.get('cr_number')
        if not value or not str(value).strip():
            raise ValidationError("CR number is required.")
        return str(value).strip().upper()

    def clean_or_number(self):
        value = self.cleaned_data.get('or_number')
        if not value or not str(value).strip():
            raise ValidationError("OR number is required.")
        return str(value).strip().upper()

    def clean_vin_number(self):
        value = self.cleaned_data.get('vin_number')
        if not value or not str(value).strip():
            raise ValidationError("VIN number is required.")
        return str(value).strip().upper()

    def clean_year_model(self):
        year = self.cleaned_data.get('year_model')
        if not year:
            raise ValidationError("Year model is required.")
        try:
            year = int(year)
            current_year = timezone.now().year
            if year < 1886 or year > current_year + 1:
                raise ValidationError(f"Year must be between 1886 and {current_year + 1}.")
            return year
        except (ValueError, TypeError):
            raise ValidationError("Please enter a valid year.")

    def clean_seat_capacity(self):
        seats = self.cleaned_data.get('seat_capacity')
        if seats is not None and str(seats).strip():
            try:
                seats = int(seats)
                if seats <= 0:
                    raise ValidationError("Seat capacity must be greater than zero.")
                return seats
            except (ValueError, TypeError):
                raise ValidationError("Please enter a valid number of seats.")
        return None

    def clean_registration_expiry(self):
        expiry = self.cleaned_data.get('registration_expiry')
        if not expiry:
            raise ValidationError("Registration expiry date is required.")
        return expiry

    def clean_license_plate(self):
        license_plate = self.cleaned_data.get('license_plate')
        if not license_plate or not str(license_plate).strip():
            raise ValidationError("License plate is required.")
        return str(license_plate).strip().upper()

    def clean_registration_number(self):
        reg_num = self.cleaned_data.get('registration_number')
        if not reg_num or not str(reg_num).strip():
            raise ValidationError("Registration number is required.")
        return str(reg_num).strip().upper()

    def clean(self):
        cleaned_data = super().clean()
        # Add any cross-field validation here if needed
        return cleaned_data


# ======================================================
# DRIVER REGISTRATION FORM
# ======================================================
class DriverRegistrationForm(forms.ModelForm):
    BLOOD_TYPE_CHOICES = [
        ('', 'Select Blood Type'),
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
        ('N/A', 'N/A'),
    ]

    LICENSE_TYPE_CHOICES = [
        ('', 'Select License Type'),
        ('Student Permit', 'Student Permit'),
        ('Non-Professional', 'Non-Professional'),
        ('Professional', 'Professional'),
        ('Conductor\'s License', 'Conductor\'s License'),
        ('Other', 'Other')
    ]

    class Meta:
        model = Driver
        exclude = ['driver_id']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'suffix': forms.TextInput(attrs={'class': 'form-control'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': 'required'}),
            'birth_place': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+63 or 09...', 'required': 'required'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@email.com', 'required': 'required'}),
            'street': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'barangay': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 6600', 'required': 'required'}),
            'city_municipality': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'province': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter license number', 'required': 'required'}),
            'license_expiry': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': 'required'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'emergency_contact_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+63 or 09...', 'required': 'required'}),
            'emergency_contact_relationship': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['blood_type'] = forms.ChoiceField(
            choices=self.BLOOD_TYPE_CHOICES,
            widget=forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            label="Blood Type"
        )
        self.fields['license_type'] = forms.ChoiceField(
            choices=self.LICENSE_TYPE_CHOICES,
            widget=forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            label="License Type"
        )

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not first_name or not first_name.strip():
            raise ValidationError("First name is required.")
        first_name = first_name.strip()
        if len(first_name) < 2:
            raise ValidationError("First name must be at least 2 characters long.")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not last_name or not last_name.strip():
            raise ValidationError("Last name is required.")
        last_name = last_name.strip()
        if len(last_name) < 2:
            raise ValidationError("Last name must be at least 2 characters long.")
        return last_name

    def clean_mobile_number(self):
        mobile_number = self.cleaned_data.get('mobile_number')
        if not mobile_number or not mobile_number.strip():
            raise ValidationError("Mobile number is required.")
            
        # Just strip whitespace, no format validation
        return mobile_number.strip()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email or not email.strip():
            raise ValidationError("Email address is required.")
            
        # Just strip whitespace, no format validation
        return email.strip()

    def clean_license_number(self):
        license_number = self.cleaned_data.get('license_number')
        if not license_number or not license_number.strip():
            raise ValidationError("License number is required.")
            
        # Just strip whitespace, no format validation
        return license_number.strip()

    def clean_license_expiry(self):
        expiry = self.cleaned_data.get('license_expiry')
        if not expiry:
            raise ValidationError("License expiry date is required.")
        return expiry

    def clean_emergency_contact_number(self):
        contact_number = self.cleaned_data.get('emergency_contact_number')
        if not contact_number or not contact_number.strip():
            raise ValidationError("Emergency contact number is required.")
        contact_number = contact_number.strip()
        if not re.match(r'^(09|\+639)\d{9}$', contact_number):
            raise ValidationError("Please en    ter a valid Philippine mobile number (e.g., 09123456789 or +639123456789).")
        return contact_number

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if not birth_date:
            raise ValidationError("Birth date is required.")
        return birth_date
        
    def clean_emergency_contact_name(self):
        contact_name = self.cleaned_data.get('emergency_contact_name')
        if not contact_name or not contact_name.strip():
            raise ValidationError("Emergency contact name is required.")
        contact_name = contact_name.strip()
        if len(contact_name) < 2:
            raise ValidationError("Emergency contact name must be at least 2 characters long.")
        return contact_name


# ======================================================
# DEPOSIT FORM
# ======================================================
class DepositForm(forms.ModelForm):
    amount = forms.DecimalField(
        label="Deposit Amount (₱)",
        min_value=1,
        decimal_places=2,
        max_digits=12,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter deposit amount'
        })
    )

    class Meta:
        model = Deposit
        fields = ['amount']
