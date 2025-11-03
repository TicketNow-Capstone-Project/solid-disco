from django import forms
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from datetime import date
import re
from .models import Driver, Vehicle, Deposit, Wallet


# ✅ Placeholder for potential extended form
class FullVehicleDetailsForm(forms.Form):
    pass


# 🟩 Enhanced Vehicle Registration Form (Strict + Fixed)
class VehicleRegistrationForm(forms.ModelForm):
    VIN_PATTERN = r"^[A-HJ-NPR-Z0-9]{17}$"  # 17 chars, excludes I, O, Q
    PLATE_PATTERN = r"^[A-Z]{3}\s?\d{3,4}$"  # ABC 1234
    OR_CR_PATTERN = r"^[A-Z0-9]{6,12}$"  # 6–12 alphanumeric
    REG_NUM_PATTERN = r"^[A-Z0-9\-]{6,12}$"

    MANUFACTURER_CHOICES = [
        ('', 'Select Manufacturer'),
        ('Toyota', 'Toyota'),
        ('Mitsubishi', 'Mitsubishi'),
        ('Nissan', 'Nissan'),
        ('Hyundai', 'Hyundai'),
        ('Kia', 'Kia'),
        ('Isuzu', 'Isuzu'),
        ('Honda', 'Honda'),
        ('Ford', 'Ford'),
        ('Suzuki', 'Suzuki'),
        ('Chevrolet', 'Chevrolet'),
        ('Other', 'Other'),
    ]

    YEAR_CHOICES = [(year, year) for year in range(2000, date.today().year + 1)]

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
            'vehicle_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter vehicle name (optional)'}),
            'vehicle_type': forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            'ownership_type': forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            'assigned_driver': forms.Select(attrs={'class': 'form-select searchable-select', 'required': 'required'}),
            'cr_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CR Number', 'required': 'required'}),
            'or_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'OR Number', 'required': 'required'}),
            'vin_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '17-character VIN', 'required': 'required'}),
            'year_model': forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Registration Number', 'required': 'required'}),
            'registration_expiry': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'required': 'required'}),
            'license_plate': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABC 1234', 'required': 'required'}),
            'manufacturer': forms.Select(attrs={'class': 'form-select', 'required': 'required'}),
            'seat_capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Number of seats'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['year_model'].choices = self.YEAR_CHOICES
        self.fields['manufacturer'].choices = self.MANUFACTURER_CHOICES
        self.fields['assigned_driver'].queryset = Driver.objects.all().order_by('first_name')
        self.fields['assigned_driver'].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name} ({obj.driver_id})"
        self.fields['vehicle_name'].required = False

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


# 🧍 Enhanced Driver Registration Form (Fixed Scope)
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

    phone_validator = RegexValidator(
        regex=r'^(?:\+63|0)9\d{9}$',
        message="Contact number must start with +63 or 09 and be 11 digits long."
    )

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

    def clean_mobile_number(self):
        number = self.cleaned_data.get('mobile_number', '')
        if number and not number.startswith(('+63', '09')):
            raise ValidationError("Mobile number must start with +63 or 09.")
        if len(number.replace('+', '').replace(' ', '')) not in [11, 12, 13]:
            raise ValidationError("Invalid mobile number length.")
        return number

    def clean_emergency_contact_number(self):
        number = self.cleaned_data.get('emergency_contact_number', '')
        if number and not number.startswith(('+63', '09')):
            raise ValidationError("Emergency contact must start with +63 or 09.")
        if len(number.replace('+', '').replace(' ', '')) not in [11, 12, 13]:
            raise ValidationError("Invalid emergency contact number length.")
        return number

    def clean_email(self):
        email = self.cleaned_data.get('email', '')
        if not email or ('.' not in email.split('@')[-1]):
            raise ValidationError("Enter a valid email address with a domain (e.g., .com, .ph).")
        return email

    def clean_zip_code(self):
        zip_code = self.cleaned_data.get('zip_code', '').strip()
        if not zip_code:
            raise ValidationError("ZIP Code is required.")
        if not zip_code.isdigit() or len(zip_code) != 4:
            raise ValidationError("ZIP Code must be a 4-digit number.")
        return zip_code


# ✅ CASH-ONLY UPDATED VERSION
class DepositForm(forms.ModelForm):
    class Meta:
        model = Deposit
        fields = ['amount']  # Only amount needed (cash only)

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
        fields = ['amount', 'payment_method']

    def save(self, commit=True):
        driver = self.cleaned_data['driver']
        amount = self.cleaned_data['amount']
        method = self.cleaned_data['payment_method']

        vehicle = Vehicle.objects.filter(assigned_driver=driver).first()
        if not vehicle:
            raise forms.ValidationError("No vehicle linked to this driver.")

        wallet = Wallet.objects.filter(vehicle=vehicle).first()
        if not wallet:
            raise forms.ValidationError("Wallet not found for this driver’s vehicle.")

        deposit = Deposit.objects.create(
            wallet=wallet,
            amount=amount,
            payment_method=method,
            status='successful' if method != 'manual' else 'pending'
        )

        if deposit.status == 'successful':
            wallet.balance += amount
            wallet.save()

        return deposit
