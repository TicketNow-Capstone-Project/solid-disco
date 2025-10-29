# vehicles/views.py
import base64
import cv2
import numpy as np
import pytesseract
import re
import json
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError

from .models import Driver, Vehicle, Wallet, Deposit
from .forms import DriverRegistrationForm, VehicleRegistrationForm

# ✅ Path for your installed Tesseract OCR (adjust if needed)
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"


# -------------------------
# OCR ENDPOINT
# -------------------------
@login_required
@csrf_exempt
@require_POST
def ocr_process(request):
    """OCR endpoint for license scanning."""
    try:
        data = json.loads(request.body)
        image_data = data.get('image_data', '')

        if not image_data:
            return JsonResponse({'error': 'No image data provided.'})

        # Decode Base64 image
        format, imgstr = image_data.split(';base64,')
        nparr = np.frombuffer(base64.b64decode(imgstr), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Preprocess image
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

        # OCR text extraction
        raw_text = pytesseract.image_to_string(thresh)
        # Debug printing available in shell if needed
        print("🧾 OCR RAW TEXT:", raw_text)

        text = re.sub(r'[^A-Za-z0-9\s:/-]', ' ', raw_text).upper()

        # Extract data patterns (best-effort; adjust regex as needed)
        license_number = re.search(r'([A-Z]{1,2}\d{2,3}-\d{2}-\d{6,7})', text)
        if not license_number:
            license_number = re.search(r'(?:[A-Z]{3}-?\d{6,7})', text)

        name_match = re.search(r'([A-Z]+),\s*([A-Z]+)\s*([A-Z]*)', text)
        birthdate = re.search(r'(\d{4}/\d{2}/\d{2})', text)
        expiry = re.search(r'(\d{4}/\d{2}/\d{2})', text)

        result = {
            'license_number': license_number.group(0) if license_number else '',
            'last_name': name_match.group(1).title() if name_match else '',
            'first_name': name_match.group(2).title() if name_match else '',
            'middle_name': name_match.group(3).title() if name_match and name_match.group(3) else '',
            'birth_date': birthdate.group(0) if birthdate else '',
            'license_expiry': expiry.group(0) if expiry else '',
        }

        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({'error': str(e)})


# -------------------------
# STAFF DASHBOARD (combined driver + vehicle)
# -------------------------
@login_required
def staff_dashboard(request):
    """Main staff dashboard showing driver + vehicle registration quick links (kept lightweight)."""
    driver_form = DriverRegistrationForm(request.POST or None, request.FILES or None)
    vehicle_form = VehicleRegistrationForm(request.POST or None)

    # Handle submissions (non-AJAX fallback) - keep minimal, but prefer dedicated pages.
    if request.method == 'POST':
        if 'driver_submit' in request.POST:
            if driver_form.is_valid():
                driver_form.save()
                messages.success(request, "✅ Driver registered successfully!")
                return redirect('staff_dashboard')
            else:
                messages.error(request, "❌ Driver form contains errors. See details below.")

        elif 'vehicle_submit' in request.POST:
            if vehicle_form.is_valid():
                try:
                    vehicle = vehicle_form.save(commit=False)
                    cd = vehicle_form.cleaned_data
                    if 'cr_number' in cd:
                        vehicle.cr_number = cd.get('cr_number') or vehicle.cr_number
                    if 'or_number' in cd:
                        vehicle.or_number = cd.get('or_number') or vehicle.or_number
                    if 'vin_number' in cd:
                        vehicle.vin_number = cd.get('vin_number') or vehicle.vin_number
                    if 'year_model' in cd:
                        vehicle.year_model = cd.get('year_model') or vehicle.year_model

                    vehicle.full_clean()
                    vehicle.save()
                    messages.success(request, f"✅ Vehicle '{vehicle.vehicle_name}' registered successfully!")
                    return redirect('staff_dashboard')
                except ValidationError as ve:
                    vehicle_form.add_error(None, ve)
                    messages.error(request, "❌ Vehicle data invalid. See form errors.")
                except Exception as e:
                    messages.error(request, f"❌ Unexpected error saving vehicle: {e}")
            else:
                messages.error(request, "❌ Vehicle form contains errors. See details below.")
        else:
            messages.error(request, "❌ Unknown submission. Try again.")

    # Dashboard stats
    total_drivers = Driver.objects.count()
    total_vehicles = Vehicle.objects.count()

    context = {
        'driver_form': driver_form,
        'vehicle_form': vehicle_form,
        'total_drivers': total_drivers,
        'total_vehicles': total_vehicles,
    }
    return render(request, 'accounts/staff_dashboard.html', context)


# -------------------------
# STANDALONE VEHICLE REGISTRATION (dedicated page)
# -------------------------
@login_required
def vehicle_registration(request):
    form = VehicleRegistrationForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            try:
                vehicle = form.save(commit=False)
                cd = form.cleaned_data
                if 'cr_number' in cd:
                    vehicle.cr_number = cd.get('cr_number') or vehicle.cr_number
                if 'or_number' in cd:
                    vehicle.or_number = cd.get('or_number') or vehicle.or_number
                if 'vin_number' in cd:
                    vehicle.vin_number = cd.get('vin_number') or vehicle.vin_number
                if 'year_model' in cd:
                    vehicle.year_model = cd.get('year_model') or vehicle.year_model

                vehicle.full_clean()
                vehicle.save()
                messages.success(request, f"✅ Vehicle '{vehicle.vehicle_name}' registered successfully!")
                return redirect('vehicles:register_vehicle')
            except ValidationError as ve:
                form.add_error(None, ve)
                messages.error(request, "❌ Vehicle data invalid. See form errors.")
            except Exception as e:
                messages.error(request, f"❌ Unexpected error saving vehicle: {e}")
        else:
            messages.error(request, "❌ Please correct the errors in the form.")

    vehicles = Vehicle.objects.select_related('assigned_driver').all().order_by('-date_registered')
    return render(request, 'vehicles/register_vehicle.html', {'form': form, 'vehicles': vehicles})


# -------------------------
# AJAX endpoints for registration (Driver & Vehicle)
# -------------------------
@login_required
@csrf_exempt
def ajax_register_driver(request):
    if request.method == 'POST':
        form = DriverRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            driver = form.save()
            return JsonResponse({
                'success': True,
                'message': f"✅ Driver '{driver.first_name} {driver.last_name}' registered successfully!"
            })
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@login_required
@csrf_exempt
def ajax_register_vehicle(request):
    if request.method == 'POST':
        form = VehicleRegistrationForm(request.POST)
        if form.is_valid():
            try:
                vehicle = form.save(commit=False)
                cd = form.cleaned_data
                if 'cr_number' in cd:
                    vehicle.cr_number = cd.get('cr_number') or vehicle.cr_number
                if 'or_number' in cd:
                    vehicle.or_number = cd.get('or_number') or vehicle.or_number
                if 'vin_number' in cd:
                    vehicle.vin_number = cd.get('vin_number') or vehicle.vin_number
                if 'year_model' in cd:
                    vehicle.year_model = cd.get('year_model') or vehicle.year_model

                vehicle.full_clean()
                vehicle.save()
                return JsonResponse({
                    'success': True,
                    'message': f"✅ Vehicle '{vehicle.vehicle_name}' registered successfully!"
                })
            except ValidationError as ve:
                return JsonResponse({'success': False, 'errors': ve.message_dict})
            except Exception as e:
                return JsonResponse({'success': False, 'errors': str(e)})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


# -------------------------
# DEDICATED STAFF PAGES (register driver/vehicle)
# -------------------------
@login_required
def register_driver(request):
    form = DriverRegistrationForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Driver registered successfully!")
            return redirect('vehicles:register_driver')
        else:
            messages.error(request, "❌ Driver form contains errors. See details below.")

    total_drivers = Driver.objects.count()
    return render(request, 'vehicles/register_driver.html', {
        'form': form,
        'total_drivers': total_drivers,
    })


@login_required
def register_vehicle(request):
    form = VehicleRegistrationForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            try:
                vehicle = form.save(commit=False)
                cd = form.cleaned_data
                if 'cr_number' in cd:
                    vehicle.cr_number = cd.get('cr_number') or vehicle.cr_number
                if 'or_number' in cd:
                    vehicle.or_number = cd.get('or_number') or vehicle.or_number
                if 'vin_number' in cd:
                    vehicle.vin_number = cd.get('vin_number') or vehicle.vin_number
                if 'year_model' in cd:
                    vehicle.year_model = cd.get('year_model') or vehicle.year_model

                vehicle.full_clean()
                vehicle.save()
                messages.success(request, f"✅ Vehicle '{vehicle.vehicle_name}' registered successfully!")
                return redirect('vehicles:register_vehicle')
            except ValidationError as ve:
                form.add_error(None, ve)
                messages.error(request, "❌ Vehicle data invalid. See form errors.")
            except Exception as e:
                messages.error(request, f"❌ Unexpected error saving vehicle: {e}")
        else:
            messages.error(request, "❌ Please correct the errors in the form.")

    vehicles = Vehicle.objects.select_related('assigned_driver').all().order_by('-date_registered')
    total_vehicles = Vehicle.objects.count()

    return render(request, 'vehicles/register_vehicle.html', {
        'form': form,
        'vehicles': vehicles,
        'total_vehicles': total_vehicles,
    })


# -------------------------
# Wallet / Deposit / QR helpers & endpoints
# -------------------------
@login_required
def get_wallet_balance(request, driver_id):
    """
    Return the wallet balance for a given driver (JSON).
    NOTE: This selects the first vehicle for that driver; change logic if your flow chooses vehicle instead.
    """
    try:
        driver = get_object_or_404(Driver, pk=driver_id)
        vehicle = driver.vehicles.first()
        if not vehicle:
            return JsonResponse({'success': False, 'message': 'Driver has no vehicle.'})
        wallet = getattr(vehicle, 'wallet', None)
        if not wallet:
            # Wallet should be auto-created by post_save signal, but handle gracefully
            wallet = Wallet.objects.create(vehicle=vehicle)
        return JsonResponse({'success': True, 'balance': float(wallet.balance)})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def vehicle_qr_view(request, vehicle_id):
    """
    Staff-only page to view/print a vehicle's QR code.
    Access: staff users only (is_staff or role == 'staff_admin').
    """
    # enforce staff-only access (admin can view list but not print)
    user_role = getattr(request.user, 'role', '')
    if not (request.user.is_staff or user_role == 'staff_admin'):
        messages.error(request, "You do not have permission to view this page.")
        return redirect('vehicles:register_vehicle')

    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    return render(request, 'vehicles/qr_detail.html', {'vehicle': vehicle})


@login_required
@csrf_exempt
def ajax_deposit(request):
    """
    AJAX endpoint to create a Deposit record and update wallet if appropriate.
    Expects POST: driver (id) OR vehicle (id) depending on frontend; here it expects 'driver'
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'})

    driver_id = request.POST.get('driver') or request.POST.get('driver_id')
    amount = request.POST.get('amount')
    payment_method = request.POST.get('payment_method', 'manual')

    if not driver_id or not amount:
        return JsonResponse({'success': False, 'message': 'Missing driver or amount.'})
    try:
        driver = get_object_or_404(Driver, pk=driver_id)
        vehicle = driver.vehicles.first()
        if not vehicle:
            return JsonResponse({'success': False, 'message': 'Driver has no vehicle.'})

        wallet = getattr(vehicle, 'wallet', None)
        if not wallet:
            wallet = Wallet.objects.create(vehicle=vehicle)

        amt = Decimal(amount)
        if amt <= 0:
            return JsonResponse({'success': False, 'message': 'Amount must be greater than zero.'})

        # create deposit (Deposit.save handles reference_number and wallet credit when status == 'successful')
        deposit = Deposit.objects.create(wallet=wallet, amount=amt, payment_method=payment_method)

        # After save, wallet may have been updated by Deposit.save (if status == 'successful')
        new_balance = float(wallet.balance)

        return JsonResponse({'success': True, 'message': 'Deposit recorded.', 'new_balance': new_balance})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
