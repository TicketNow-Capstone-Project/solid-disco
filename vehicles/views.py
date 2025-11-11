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
from django.views.decorators.cache import never_cache
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone

from accounts.utils import is_staff_admin_or_admin, is_admin
from .models import Driver, Vehicle, Wallet, Deposit, QueueHistory
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

        format, imgstr = image_data.split(';base64,')
        nparr = np.frombuffer(base64.b64decode(imgstr), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

        raw_text = pytesseract.image_to_string(thresh)
        print("🧾 OCR RAW TEXT:", raw_text)
        text = re.sub(r'[^A-Za-z0-9\s:/-]', ' ', raw_text).upper()

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
# STAFF DASHBOARD
# -------------------------
@login_required
@user_passes_test(is_staff_admin_or_admin)
def staff_dashboard(request):
    """Main staff dashboard showing driver + vehicle registration quick links."""
    driver_form = DriverRegistrationForm(request.POST or None, request.FILES or None)
    vehicle_form = VehicleRegistrationForm(request.POST or None)

    if request.method == 'POST':
        if 'driver_submit' in request.POST:
            if driver_form.is_valid():
                driver_form.save()
                messages.success(request, "✅ Driver registered successfully!")
                return redirect('staff_dashboard')
            else:
                messages.error(request, "❌ Driver form contains errors.")

        elif 'vehicle_submit' in request.POST:
            if vehicle_form.is_valid():
                try:
                    vehicle = vehicle_form.save(commit=False)
                    cd = vehicle_form.cleaned_data

                    # ✅ Assign selected route
                    if cd.get('route'):
                        vehicle.route = cd['route']

                    # Other field validations (safeguard)
                    for field in ['cr_number', 'or_number', 'vin_number', 'year_model']:
                        if field in cd:
                            setattr(vehicle, field, cd.get(field) or getattr(vehicle, field))

                    vehicle.full_clean()
                    vehicle.save()
                    messages.success(request, f"✅ Vehicle '{vehicle.vehicle_name}' registered successfully!")
                    return redirect('staff_dashboard')
                except ValidationError as ve:
                    vehicle_form.add_error(None, ve)
                    messages.error(request, "❌ Invalid vehicle data.")
                except Exception as e:
                    messages.error(request, f"❌ Unexpected error: {e}")
            else:
                messages.error(request, "❌ Vehicle form contains errors.")

    context = {
        'driver_form': driver_form,
        'vehicle_form': vehicle_form,
        'total_drivers': Driver.objects.count(),
        'total_vehicles': Vehicle.objects.count(),
    }
    return render(request, 'accounts/staff_dashboard.html', context)


# -------------------------
# VEHICLE REGISTRATION (page)
# -------------------------
@login_required
@user_passes_test(is_staff_admin_or_admin)
def vehicle_registration(request):
    form = VehicleRegistrationForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            try:
                vehicle = form.save(commit=False)
                cd = form.cleaned_data

                # ✅ Assign route
                if cd.get('route'):
                    vehicle.route = cd['route']

                for field in ['cr_number', 'or_number', 'vin_number', 'year_model']:
                    if field in cd:
                        setattr(vehicle, field, cd.get(field) or getattr(vehicle, field))

                vehicle.full_clean()
                vehicle.save()
                messages.success(request, f"✅ Vehicle '{vehicle.vehicle_name}' registered successfully!")
                return redirect('vehicles:register_vehicle')
            except ValidationError as ve:
                form.add_error(None, ve)
                messages.error(request, "❌ Invalid vehicle data.")
            except Exception as e:
                messages.error(request, f"❌ Unexpected error: {e}")
        else:
            messages.error(request, "❌ Please correct the errors.")

    vehicles = Vehicle.objects.select_related('assigned_driver', 'route').all().order_by('-date_registered')
    return render(request, 'vehicles/register_vehicle.html', {'form': form, 'vehicles': vehicles})


# -------------------------
# AJAX ENDPOINTS
# -------------------------
@login_required
@user_passes_test(is_staff_admin_or_admin)
@csrf_exempt
def ajax_register_driver(request):
    if request.method == 'POST':
        form = DriverRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            driver = form.save()
            return JsonResponse({'success': True, 'message': f"✅ Driver '{driver.first_name} {driver.last_name}' registered successfully!"})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    return JsonResponse({'success': False, 'message': 'Invalid request.'})


@login_required
@user_passes_test(is_staff_admin_or_admin)
@csrf_exempt
def ajax_register_vehicle(request):
    if request.method == 'POST':
        form = VehicleRegistrationForm(request.POST)
        if form.is_valid():
            try:
                vehicle = form.save(commit=False)
                cd = form.cleaned_data

                # ✅ Assign route
                if cd.get('route'):
                    vehicle.route = cd['route']

                for field in ['cr_number', 'or_number', 'vin_number', 'year_model']:
                    if field in cd:
                        setattr(vehicle, field, cd.get(field) or getattr(vehicle, field))

                vehicle.full_clean()
                vehicle.save()
                return JsonResponse({'success': True, 'message': f"✅ Vehicle '{vehicle.vehicle_name}' registered successfully!"})
            except ValidationError as ve:
                return JsonResponse({'success': False, 'errors': ve.message_dict})
            except Exception as e:
                return JsonResponse({'success': False, 'errors': str(e)})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    return JsonResponse({'success': False, 'message': 'Invalid request.'})


# -------------------------
# DEDICATED STAFF PAGES
# -------------------------
@login_required
@user_passes_test(is_staff_admin_or_admin)
def register_driver(request):
    form = DriverRegistrationForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Driver registered successfully!")
            return redirect('vehicles:register_driver')
        else:
            messages.error(request, "❌ Driver form contains errors.")
    total_drivers = Driver.objects.count()
    return render(request, 'vehicles/register_driver.html', {'form': form, 'total_drivers': total_drivers})


@login_required
@user_passes_test(is_staff_admin_or_admin)
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
                messages.error(request, "❌ Vehicle data invalid.")
            except Exception as e:
                messages.error(request, f"❌ Unexpected error: {e}")
        else:
            messages.error(request, "❌ Please correct the errors.")
    vehicles = Vehicle.objects.select_related('assigned_driver').all().order_by('-date_registered')
    total_vehicles = Vehicle.objects.count()
    return render(request, 'vehicles/register_vehicle.html', {'form': form, 'vehicles': vehicles, 'total_vehicles': total_vehicles})


# -------------------------
# WALLET & DEPOSITS
# -------------------------
@login_required
def get_wallet_balance(request, driver_id):
    try:
        driver = get_object_or_404(Driver, pk=driver_id)
        vehicle = driver.vehicles.first()
        if not vehicle:
            return JsonResponse({'success': False, 'message': 'Driver has no vehicle.'})
        wallet = getattr(vehicle, 'wallet', None) or Wallet.objects.create(vehicle=vehicle)
        return JsonResponse({'success': True, 'balance': float(wallet.balance)})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@user_passes_test(is_staff_admin_or_admin)
def vehicle_qr_view(request, vehicle_id):
    user_role = getattr(request.user, 'role', '')
    if not (request.user.is_staff or user_role in ['staff_admin', 'admin']):
        messages.error(request, "You do not have permission to view this page.")
        return redirect('vehicles:register_vehicle')
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    return render(request, 'vehicles/qr_detail.html', {'vehicle': vehicle})


@login_required
@csrf_exempt
def ajax_deposit(request):
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
        wallet = getattr(vehicle, 'wallet', None) or Wallet.objects.create(vehicle=vehicle)
        amt = Decimal(amount)
        if amt <= 0:
            return JsonResponse({'success': False, 'message': 'Amount must be greater than zero.'})
        deposit = Deposit.objects.create(wallet=wallet, amount=amt, payment_method=payment_method)
        return JsonResponse({'success': True, 'message': 'Deposit recorded.', 'new_balance': float(wallet.balance)})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


# -------------------------
# REGISTERED VEHICLES / DRIVERS
# -------------------------
@login_required
@user_passes_test(is_staff_admin_or_admin)
def registered_vehicles(request):
    vehicle_list = Vehicle.objects.select_related('assigned_driver').order_by('-date_registered')
    paginator = Paginator(vehicle_list, 10)
    vehicles = paginator.get_page(request.GET.get('page'))
    return render(request, 'vehicles/registered_vehicles.html', {'vehicles': vehicles})


@login_required
@user_passes_test(is_staff_admin_or_admin)
def registered_drivers(request):
    query = request.GET.get('q', '').strip()
    driver_list = Driver.objects.all().order_by('-id')
    if query:
        driver_list = driver_list.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(middle_name__icontains=query) |
            Q(license_number__icontains=query) |
            Q(mobile_number__icontains=query)
        )
    paginator = Paginator(driver_list, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'vehicles/registered_drivers.html', {'page_obj': page_obj})


@login_required
def get_vehicles_by_driver(request, driver_id):
    vehicles = Vehicle.objects.filter(assigned_driver_id=driver_id)
    data = {"vehicles": [{"id": v.id, "license_plate": v.license_plate, "vehicle_name": v.vehicle_name} for v in vehicles]}
    return JsonResponse(data)


# -------------------------
# DELETE DRIVER / VEHICLE
# -------------------------
@login_required
@user_passes_test(is_admin)
@never_cache
def delete_driver(request, driver_id):
    driver = get_object_or_404(Driver, id=driver_id)
    if request.method == 'POST':
        driver_name = f"{driver.first_name} {driver.last_name}"
        driver.delete()
        messages.success(request, f"✅ Driver '{driver_name}' deleted successfully.")
        return redirect('vehicles:registered_drivers')
    return redirect('vehicles:registered_drivers')


@login_required
@user_passes_test(is_admin)
@never_cache
def delete_vehicle(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    if request.method == 'POST':
        vehicle_name = vehicle.vehicle_name
        vehicle.delete()
        messages.success(request, f"✅ Vehicle '{vehicle_name}' deleted successfully.")
        return redirect('vehicles:registered_vehicles')
    return redirect('vehicles:registered_vehicles')


# -------------------------
# QR ENTRY & EXIT HANDLERS
# -------------------------
@login_required
@csrf_exempt
def qr_entry(request):
    """
    Triggered when vehicle QR is scanned on ENTRY.
    Sets status to 'boarding', computes departure_time (+30 mins default),
    and logs QueueHistory.
    """
    qr_value = request.POST.get('qr_value')
    if not qr_value:
        return JsonResponse({'success': False, 'message': 'Missing QR value.'})

    try:
        vehicle = get_object_or_404(Vehicle, qr_value=qr_value)
        now = timezone.now()
        vehicle.status = 'boarding'
        vehicle.last_enter_time = now
        vehicle.departure_time = now + timezone.timedelta(minutes=30)  # default waiting time
        vehicle.save(update_fields=['status', 'last_enter_time', 'departure_time'])

        QueueHistory.objects.create(
            vehicle=vehicle,
            driver=vehicle.assigned_driver,
            action='enter',
            departure_time_snapshot=vehicle.departure_time,
            wallet_balance_snapshot=vehicle.wallet.balance
        )
        return JsonResponse({'success': True, 'message': f"{vehicle.license_plate} entered terminal.", 'departure_time': vehicle.departure_time})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@csrf_exempt
def qr_exit(request):
    """
    Triggered when vehicle QR is scanned on EXIT.
    Sets status to 'departed', keeps it for 10 mins, logs QueueHistory.
    """
    qr_value = request.POST.get('qr_value')
    if not qr_value:
        return JsonResponse({'success': False, 'message': 'Missing QR value.'})

    try:
        vehicle = get_object_or_404(Vehicle, qr_value=qr_value)
        now = timezone.now()
        vehicle.status = 'departed'
        vehicle.last_exit_time = now
        vehicle.save(update_fields=['status', 'last_exit_time'])

        QueueHistory.objects.create(
            vehicle=vehicle,
            driver=vehicle.assigned_driver,
            action='exit',
            departure_time_snapshot=vehicle.departure_time,
            wallet_balance_snapshot=vehicle.wallet.balance
        )

        return JsonResponse({'success': True, 'message': f"{vehicle.license_plate} departed terminal."})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


# -------------------------
# ADMIN DASHBOARD DATA (7-day trend)
# -------------------------
@login_required
@user_passes_test(is_admin)
def admin_dashboard_data(request):
    """Return JSON with 7-day profit trend and live stats."""
    from django.db.models.functions import TruncDate
    from datetime import timedelta

    now = timezone.now()
    seven_days_ago = now - timedelta(days=6)

    # Group deposits by date
    daily_profits = (
        Deposit.objects.filter(created_at__date__gte=seven_days_ago.date())
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(total=Sum('amount'))
        .order_by('day')
    )

    # Ensure we produce labels for each of the last 7 days (even if 0)
    labels = []
    data_points = []
    for i in range(6, -1, -1):  # 6 -> 0 (six days ago .. today)
        d = (now - timedelta(days=i)).date()
        labels.append(d.strftime('%b %d'))
        matching = next((item for item in daily_profits if item['day'].date() == d), None)
        data_points.append(float(matching['total']) if matching else 0.0)

    total_drivers = Driver.objects.count()
    total_vehicles = Vehicle.objects.count()
    total_deposits = Deposit.objects.aggregate(total=Sum('amount'))['total'] or 0
    total_wallets = Wallet.objects.aggregate(total=Sum('balance'))['total'] or 0

    recent_deposits = list(
        Deposit.objects.select_related('wallet__vehicle')
        .order_by('-created_at')[:5]
        .values('reference_number', 'amount', 'created_at', 'wallet__vehicle__license_plate')
    )

    recent_queues = list(
        QueueHistory.objects.select_related('vehicle')
        .order_by('-timestamp')[:5]
        .values('vehicle__license_plate', 'action', 'timestamp')
    )

    data = {
        'total_drivers': total_drivers,
        'total_vehicles': total_vehicles,
        'total_profit': float(total_deposits),
        'wallet_total': float(total_wallets),
        'recent_deposits': recent_deposits,
        'recent_queues': recent_queues,
        'chart_labels': labels,
        'chart_data': data_points,
    }
    return JsonResponse(data)


# -------------------------
# QUEUE HISTORY VIEW (for admin)
# -------------------------
@login_required
@user_passes_test(is_admin)
def queue_history(request):
    history = QueueHistory.objects.select_related('vehicle', 'driver').order_by('-timestamp')
    paginator = Paginator(history, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'terminal/queue_history.html', {'page_obj': page})

