from django import forms
from django.core.validators import RegexValidator
from .models import Driver, Vehicle, Deposit, Wallet


# ✅ (Keep your original long one but rename it)
class FullVehicleDetailsForm(forms.Form):
    # Vehicle Basic Information
    plate_number = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'ABC 123',
            'pattern': '[A-Z]{2,3} [0-9]{3,4}'
        })
    )
    mv_file_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'MV File Number'})
    )

    # Vehicle Identification
    cr_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Certificate of Registration Number'})
    )
    or_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Official Receipt Number'})
    )
    engine_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Engine Number'})
    )
    chassis_number = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Chassis Number'})
    )

    # Vehicle Details
    make = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Toyota, Mitsubishi, etc.'})
    )
    model = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Vios, Montero, etc.'})
    )
    series = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Series/Variant'})
    )
    year_model = forms.IntegerField(
        min_value=1900,
        max_value=2030,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '2024'})
    )

    # Vehicle Classification
    body_type = forms.ChoiceField(
        choices=[
            ('', 'Select Body Type'),
            ('Sedan', 'Sedan'),
            ('SUV', 'SUV'),
            ('MPV/AUV', 'MPV/AUV'),
            ('Van', 'Van'),
            ('Pickup', 'Pickup'),
            ('Truck', 'Truck'),
            ('Bus', 'Bus'),
            ('Motorcycle', 'Motorcycle'),
            ('Other', 'Other'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    color = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Color'})
    )
    gross_vehicle_weight = forms.DecimalField(
        max_digits=8,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'})
    )
    net_capacity = forms.DecimalField(
        max_digits=8,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'})
    )

    # Registration Details
    date_of_issuance = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_of_expiry = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    # Fuel Type
    fuel_type = forms.ChoiceField(
        choices=[
            ('', 'Select Fuel Type'),
            ('Gasoline', 'Gasoline'),
            ('Diesel', 'Diesel'),
            ('Electric', 'Electric'),
            ('Hybrid', 'Hybrid'),
            ('LPG', 'LPG'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    # Ownership Details
    owner_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Registered Owner Name'})
    )
    owner_address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'placeholder': 'Complete address of registered owner',
            'rows': 3
        })
    )

    # Insurance Information
    insurance_company = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Insurance Company'})
    )
    insurance_policy_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Policy Number'})
    )
    insurance_expiry = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )


# ✅ Vehicle Registration Form
class VehicleRegistrationForm(forms.ModelForm):
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
            'vehicle_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter vehicle name'}),
            'vehicle_type': forms.Select(attrs={'class': 'form-select'}),
            'ownership_type': forms.Select(attrs={'class': 'form-select'}),
            'assigned_driver': forms.Select(attrs={'class': 'form-select searchable-select'}),
            'cr_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CR Number'}),
            'or_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'OR Number'}),
            'vin_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VIN'}),
            'year_model': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Year Model'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Registration Number'}),
            'registration_expiry': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'license_plate': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABC 123'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Manufacturer (e.g., Toyota)'}),
            'seat_capacity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Number of seats'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_driver'].queryset = Driver.objects.all().order_by('first_name')
        self.fields['assigned_driver'].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name} ({obj.driver_id})"


# ✅ Driver Registration Form
class DriverRegistrationForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = '__all__'
        exclude = ['driver_id']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'suffix': forms.TextInput(attrs={'class': 'form-control'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'birth_place': forms.TextInput(attrs={'class': 'form-control'}),
            'blood_type': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'house_number': forms.TextInput(attrs={'class': 'form-control'}),
            'street': forms.TextInput(attrs={'class': 'form-control'}),
            'barangay': forms.TextInput(attrs={'class': 'form-control'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control'}),
            'city_municipality': forms.TextInput(attrs={'class': 'form-control'}),
            'province': forms.TextInput(attrs={'class': 'form-control'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'license_expiry': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'license_type': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_relationship': forms.TextInput(attrs={'class': 'form-control'}),
        }


# ✅ Deposit Form (new)
class DepositForm(forms.ModelForm):
    driver = forms.ModelChoiceField(
        queryset=Driver.objects.all().order_by('first_name'),
        widget=forms.Select(attrs={'class': 'form-select searchable-select'}),
        label="Select Driver"
    )
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter deposit amount'}),
        label="Deposit Amount"
    )
    payment_method = forms.ChoiceField(
        choices=Deposit.PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Payment Method"
    )

    class Meta:
        model = Deposit
        fields = ['amount', 'payment_method']

    def save(self, commit=True):
        """
        Custom save method:
        - Finds the driver's active vehicle & wallet
        - Creates deposit record
        - Updates wallet balance if successful
        """
        driver = self.cleaned_data['driver']
        amount = self.cleaned_data['amount']
        method = self.cleaned_data['payment_method']

        # Get the vehicle assigned to this driver
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

        # Update wallet balance immediately for manual deposits
        if deposit.status == 'successful':
            wallet.balance += amount
            wallet.save()

        return deposit
