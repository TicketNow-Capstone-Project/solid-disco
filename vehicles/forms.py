from django import forms
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from datetime import date
import re
from .models import Driver, Vehicle, Deposit, Wallet
from terminal.models import SystemSettings

# ✅ Placeholder for potential extended form
class FullVehicleDetailsForm(forms.Form):
    pass


class VehicleRegistrationForm(forms.ModelForm):
    VIN_PATTERN = r"^[A-HJ-NPR-Z0-9]{17}$"  # 17 chars, excludes I, O, Q
    PLATE_PATTERN = r"^[A-Z]{3}\s?\d{3,4}$"  # ABC 1234
    OR_CR_PATTERN = r"^[A-Z0-9]{6,12}$"      # 6–12 alphanumeric
    REG_NUM_PATTERN = r"^[A-Z0-9\-]{6,12}$"  # Alphanumeric registration

    # 🇵🇭 Common Jeepney, Van, and Bus brands in the Philippines
    MANUFACTURER_CHOICES = [
        ('', 'Select Manufacturer'),
        # 🚌 Bus brands
        ('Hino', 'Hino'),
        ('Isuzu', 'Isuzu'),
        ('Fuso', 'Fuso'),
        ('Daewoo', 'Daewoo'),
        ('Hyundai', 'Hyundai'),
        ('King Long', 'King Long'),
        ('Yutong', 'Yutong'),
        ('Golden Dragon', 'Golden Dragon'),
        # 🚐 Van brands
        ('Toyota', 'Toyota'),
        ('Nissan', 'Nissan'),
        ('Hyundai (Van)', 'Hyundai'),
        ('Kia', 'Kia'),
        ('Foton', 'Foton'),
        ('Maxus', 'Maxus'),
        # 🚙 Jeepney / Modern Jeepney brands
        ('Sarao', 'Sarao Motors'),
        ('Francisco', 'Francisco Motors'),
        ('Hyundai Modern Jeepney', 'Hyundai Modern Jeepney'),
        ('Isuzu Modern Jeepney', 'Isuzu Modern Jeepney'),
        ('Foton Modern Jeepney', 'Foton Modern Jeepney'),
        ('Hino Modern Jeepney', 'Hino Modern Jeepney'),
        ('Other', 'Other'),
    ]

    class Meta:
        model = Vehicle
        fields = [
            'vehicle_name',
            'vehicle_type',
            'ownership_type',
            'assigned_driver',
            'cr_number',
            'or_number',
            'vin_number',
            'year_model',
            'registration_number',
            'registration_expiry',
            'license_plate',
            'manufacturer',
            'seat_capacity',
        ]
        widgets = {
            'vehicle_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter vehicle name (optional)'
            }),
            'vehicle_type': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'ownership_type': forms.Select(attrs={
                'class': 'form-select',
                'required': 'required'
            }),
            'assigned_driver': forms.Select(attrs={
                'class': 'form-select searchable-select',
                'required': 'required'
            }),
            'cr_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CR Number',
                'required': 'required'
            }),
            'or_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'OR Number',
                'required': 'required'
            }),
            'vin_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '17-character VIN',
                'required': 'required'
            }),
            # ✅ Typable year model
            'year_model': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 2024',
                'min': '1900',
                'max': '2100',
                'required': 'required'
            }),
            'registration_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Registration Number',
                'required': 'required'
            }),
            'registration_expiry': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'required': 'required'
            }),
            'license_plate': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ABC 1234',
                'required': 'required'
            }),
            # 🟩 visible and clean manufacturer dropdown
            'manufacturer': forms.Select(attrs={
                'class': 'form-select text-dark bg-white border',
                'style': 'color:black;background-color:white;',
                'required': 'required'
            }),
            'seat_capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'Number of seats'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['manufacturer'].choices = self.MANUFACTURER_CHOICES
        self.fields['assigned_driver'].queryset = Driver.objects.all().order_by('first_name')
        self.fields['assigned_driver'].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name} ({obj.driver_id})"
        self.fields['vehicle_name'].required = False

    def clean_seat_capacity(self):
        seat_capacity = self.cleaned_data.get('seat_capacity')
        vehicle_type = self.cleaned_data.get('vehicle_type')

        if not seat_capacity:
            raise ValidationError("Seat capacity is required.")
        if seat_capacity < 1:
            raise ValidationError("Seat capacity must be at least 1.")

        settings = SystemSettings.get_solo()
        limits = {
            'jeepney': getattr(settings, 'jeepney_max_seats', 25),
            'van': getattr(settings, 'van_max_seats', 15),
            'bus': getattr(settings, 'bus_max_seats', 60),
        }

        if vehicle_type:
            vehicle_type = vehicle_type.lower()
            max_allowed = limits.get(vehicle_type)
            if max_allowed and seat_capacity > max_allowed:
                raise ValidationError(
                    f"{vehicle_type.title()} seat capacity cannot exceed {max_allowed} seats (LTO limit)."
                )
        return seat_capacity

    def clean_cr_number(self):
        cr = self.cleaned_data.get('cr_number', '').upper()
        if not re.match(self.OR_CR_PATTERN, cr):
            raise ValidationError("CR number must be 6–12 alphanumeric characters.")
        return cr

    def clean_or_number(self):
        or_num = self.cleaned_data.get('or_number', '').upper()
        if not re.match(self.OR_CR_PATTERN, or_num):
            raise ValidationError("OR number must be 6–12 alphanumeric characters.")
        return or_num

    def clean_vin_number(self):
        vin = self.cleaned_data.get('vin_number', '').upper()
        if not re.match(self.VIN_PATTERN, vin):
            raise ValidationError("VIN must be exactly 17 alphanumeric characters (excluding I, O, Q).")
        return vin

    def clean_registration_number(self):
        reg = self.cleaned_data.get('registration_number', '').upper()
        if not re.match(self.REG_NUM_PATTERN, reg):
            raise ValidationError("Registration number must be 6–12 alphanumeric characters.")
        return reg

    def clean_registration_expiry(self):
        expiry = self.cleaned_data.get('registration_expiry')
        if expiry and expiry < date.today():
            raise ValidationError("Registration has already expired.")
        return expiry

    def clean_license_plate(self):
        plate = self.cleaned_data.get('license_plate', '').upper()
        if not re.match(self.PLATE_PATTERN, plate):
            raise ValidationError("License plate must follow format: ABC 1234.")
        return plate


# 🧍 Enhanced Driver Registration Form (unchanged)
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
        ('Professional Driver\'s License', 'Professional Driver\'s License'),
        ('Non-Professional Driver\'s License', 'Non-Professional Driver\'s License'),
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

    def clean_license_expiry(self):
        expiry = self.cleaned_data.get('license_expiry')
        if expiry and expiry < date.today():
            raise ValidationError("Driver's license is expired. Please renew before registering.")
        return expiry


# ✅ Simplified Cash-Only Deposit Form
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
