from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache
from django.http import JsonResponse, HttpResponse
from vehicles.models import Vehicle, Wallet, Driver, Deposit  # 🟩 Added models
from .models import EntryLog, SystemSettings
from decimal import Decimal
from django import forms
from django.contrib import messages
from django.utils import timezone
import csv
from datetime import timedelta


# 🔐 Helper: Check if user is staff
def is_staff_admin(user):
    return user.is_authenticated and (user.is_staff or getattr(user, 'role', '') == 'staff_admin')


@login_required(login_url='login')
@user_passes_test(is_staff_admin)
@never_cache
def deposit_menu(request):
    """
    Allows staff to record cash-only deposits instantly to a driver's wallet.
    Automatically updates the wallet balance and logs the transaction.
    """

    settings = SystemSettings.get_solo()
    min_deposit = settings.min_deposit_amount

    # 🟩 Drivers that have at least one registered vehicle
    drivers_with_vehicles = (
        Driver.objects
        .filter(vehicles__isnull=False)
        .distinct()
        .order_by('last_name', 'first_name')
    )

    # 🟩 Recent deposits (for display)
    recent_deposits = (
        Deposit.objects
        .select_related('wallet__vehicle__assigned_driver')
        .order_by('-created_at')[:10]
    )

    # 🟩 Deposit form submission
    if request.method == "POST":
        driver_id = request.POST.get("driver_id")
        vehicle_id = request.POST.get("vehicle_id")
        amount_str = request.POST.get("amount", "").strip()

        # Validation
        if not all([driver_id, vehicle_id, amount_str]):
            messages.error(request, "⚠️ Please fill in all required fields.")
            return redirect('terminal:deposit_menu')

        try:
            amount = Decimal(amount_str)
        except:
            messages.error(request, "❌ Invalid deposit amount.")
            return redirect('terminal:deposit_menu')

        if amount <= 0:
            messages.error(request, "⚠️ Deposit amount must be greater than zero.")
            return redirect('terminal:deposit_menu')

        # Get the driver, vehicle, and wallet
        vehicle = Vehicle.objects.filter(id=vehicle_id).first()
        if not vehicle:
            messages.error(request, "❌ Vehicle not found.")
            return redirect('terminal:deposit_menu')

        wallet, _ = Wallet.objects.get_or_create(vehicle=vehicle)

        # 💰 Create Deposit (cash-only, instantly applied)
        deposit = Deposit.objects.create(
            wallet=wallet,
            amount=amount,
        )

        messages.success(
            request,
            f"✅ Successfully deposited ₱{amount} to {vehicle.license_plate}."
        )
        return redirect('terminal:deposit_menu')

    # 🟦 Context for template
    context_message = "" if drivers_with_vehicles.exists() else \
        "No registered drivers with vehicles found. Please register a vehicle first."

    context = {
        "drivers": drivers_with_vehicles,
        "recent_deposits": recent_deposits,
        "context_message": context_message,
        "min_deposit": min_deposit,
    }

    return render(request, "terminal/deposit_menu.html", context)


# ✅ Terminal Queue View
@login_required(login_url='login')
@user_passes_test(is_staff_admin)
@never_cache
def terminal_queue(request):
    """Displays live queue of recent validated vehicle entries."""
    return render(request, 'terminal/terminal_queue.html')


# 🆕 STEP 3.5: AJAX endpoint — Live Queue Data
@login_required(login_url='login')
@user_passes_test(is_staff_admin)
@never_cache
def queue_data(request):
    """
    Returns the latest EntryLog records as JSON for live queue refresh.
    Only includes active (non-departed) entries.
    """
    logs = (
        EntryLog.objects
        .filter(status=EntryLog.STATUS_SUCCESS, is_active=True)
        .select_related("vehicle__assigned_driver", "staff")
        .order_by("-created_at")[:20]
    )

    data = []
    for log in logs:
        vehicle = log.vehicle
        driver = vehicle.assigned_driver if vehicle else None

        data.append({
            "id": log.id,
            "vehicle_plate": getattr(vehicle, "license_plate", "N/A") if vehicle else "—",
            "vehicle_name": getattr(vehicle, "vehicle_name", "—") if vehicle else "—",
            "driver_name": f"{driver.first_name} {driver.last_name}" if driver else "—",
            "fee": float(log.fee_charged),
            "staff": log.staff.username if log.staff else "—",
            "time": log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        })

    return JsonResponse({"entries": data})




@login_required(login_url='login')
@user_passes_test(is_staff_admin)
@never_cache
def simple_queue_view(request):
    """
    Display-only view for the terminal TV screens.
    Shows plate, driver, entry time, and calculated departure time.
    """
    settings = SystemSettings.get_solo()
    duration = getattr(settings, "departure_duration_minutes", 30)

    logs = (
        EntryLog.objects
        .filter(is_active=True, status=EntryLog.STATUS_SUCCESS)
        .select_related("vehicle__assigned_driver")
        .order_by("-created_at")
    )

    queue = []
    for log in logs:
        vehicle = log.vehicle
        driver = vehicle.assigned_driver if vehicle else None
        departure_time = log.created_at + timedelta(minutes=duration)

        queue.append({
            "plate": getattr(vehicle, "license_plate", "N/A"),
            "driver": f"{driver.first_name} {driver.last_name}" if driver else "N/A",
            "entry_time": timezone.localtime(log.created_at).strftime("%I:%M %p"),
            "departure_time": timezone.localtime(departure_time).strftime("%I:%M %p"),
        })

    context = {
        "queue": queue,
        "stay_duration": duration,
        "now": timezone.localtime(timezone.now()),  # 🕒 pass current time
    }
    return render(request, "terminal/simple_queue.html", context)



# 🟢 Manage Queue View (Staff Control Panel)
@login_required(login_url='login')
@user_passes_test(is_staff_admin)
@never_cache
def manage_queue(request):
    """
    Staff view for managing active terminal entries.
    Displays all active vehicles, allows marking as departed
    or adjusting departure time manually.
    """
    settings = SystemSettings.get_solo()
    duration = getattr(settings, "departure_duration_minutes", 30)

    logs = (
        EntryLog.objects
        .filter(is_active=True, status=EntryLog.STATUS_SUCCESS)
        .select_related("vehicle__assigned_driver", "staff")
        .order_by("-created_at")
    )

    queue = []
    for log in logs:
        vehicle = log.vehicle
        driver = vehicle.assigned_driver if vehicle else None
        departure_time = log.created_at + timedelta(minutes=duration)

        queue.append({
            "id": log.id,
            "plate": getattr(vehicle, "license_plate", "N/A"),
            "driver": f"{driver.first_name} {driver.last_name}" if driver else "N/A",
            "entry_time": timezone.localtime(log.created_at).strftime("%I:%M %p"),
            "departure_time": timezone.localtime(departure_time).strftime("%I:%M %p"),
            "staff": log.staff.username if log.staff else "—",
        })

    context = {
        "queue": queue,
        "stay_duration": duration,
    }
    return render(request, "terminal/manage_queue.html", context)








# 🟩 STEP 4.1: QR Scan Entry + Departure Logic
@login_required(login_url='login')
@user_passes_test(is_staff_admin)
@never_cache
def qr_scan_entry(request):
    """
    Handles QR scans for both ENTRY and DEPARTURE validation.
    - If vehicle has no active entry → process as ENTRY (deduct fee, create log)
    - If vehicle already has an active entry → process as DEPARTURE (mark departed)
    """
    settings = SystemSettings.get_solo()
    entry_fee = settings.terminal_fee
    cooldown_minutes = settings.entry_cooldown_minutes
    min_deposit = settings.min_deposit_amount

    if request.method == "POST":
        qr_code = request.POST.get("qr_code", "").strip()
        if not qr_code:
            return JsonResponse({"status": "error", "message": "QR code is empty. Please try again."})

        staff_user = request.user

        try:
            vehicle = Vehicle.objects.filter(qr_value__iexact=qr_code.strip()).first()
            if not vehicle:
                return JsonResponse({
                    "status": "error",
                    "message": "No vehicle found for this QR code. Please make sure it's valid."
                })

            wallet = Wallet.objects.filter(vehicle=vehicle).first()
            if not wallet:
                return JsonResponse({
                    "status": "error",
                    "message": "No wallet found for this vehicle. Please deposit funds first."
                })

            from datetime import timedelta, timezone, datetime
            now = datetime.now(timezone.utc)

            # 🟦 Check if vehicle has an active log → DEPARTURE
            active_log = EntryLog.objects.filter(vehicle=vehicle, is_active=True).first()
            if active_log:
                active_log.is_active = False
                active_log.departed_at = timezone.now()
                active_log.message = f"Vehicle '{vehicle.license_plate}' departed at {timezone.localtime(active_log.departed_at).strftime('%I:%M %p')}."
                active_log.save(update_fields=["is_active", "departed_at", "message"])

                return JsonResponse({
                    "status": "success",
                    "message": f"✅ Vehicle '{vehicle.license_plate}' successfully departed at {timezone.localtime(active_log.departed_at).strftime('%I:%M %p')}."
                })

            # 🟩 Otherwise, process ENTRY logic
            recent_entry = (
                EntryLog.objects.filter(vehicle=vehicle, status=EntryLog.STATUS_SUCCESS)
                .order_by("-created_at")
                .first()
            )
            if recent_entry and (now - recent_entry.created_at) < timedelta(minutes=cooldown_minutes):
                return JsonResponse({
                    "status": "error",
                    "message": f"⏳ Vehicle '{vehicle.license_plate}' entered recently. "
                               f"Please wait {cooldown_minutes} minute(s) before re-entry."
                })

            # 💰 Check minimum deposit requirement
            if wallet.balance < min_deposit:
                return JsonResponse({
                    "status": "error",
                    "message": f"⚠️ Minimum deposit of ₱{min_deposit} required before entry. "
                               "Please add funds at the deposit counter."
                })

            # ✅ Check sufficient balance for entry fee
            if wallet.balance >= entry_fee:
                wallet.balance -= entry_fee
                wallet.save()

                EntryLog.objects.create(
                    vehicle=vehicle,
                    staff=staff_user,
                    fee_charged=entry_fee,
                    status=EntryLog.STATUS_SUCCESS,
                    message=f"Vehicle '{vehicle.license_plate}' entered terminal. ₱{entry_fee} deducted."
                )

                return JsonResponse({
                    "status": "success",
                    "message": f"🚗 Vehicle '{vehicle.license_plate}' successfully entered terminal. ₱{entry_fee} deducted."
                })
            else:
                EntryLog.objects.create(
                    vehicle=vehicle,
                    staff=staff_user,
                    fee_charged=entry_fee,
                    status=EntryLog.STATUS_INSUFFICIENT,
                    message=f"Insufficient balance for vehicle '{vehicle.license_plate}'."
                )
                return JsonResponse({
                    "status": "error",
                    "message": f"❌ Insufficient balance for vehicle '{vehicle.license_plate}'. "
                               f"Deposit at least ₱{entry_fee}."
                })

        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Unexpected error: {str(e)}"})

    context = {
        "terminal_fee": entry_fee,
        "min_deposit": min_deposit,
        "cooldown": cooldown_minutes,
    }
    return render(request, "terminal/qr_scan_entry.html", context)


# 🟩 STEP 4.1: QR Exit Validation (Auto-Depart via Re-Scan)
@login_required(login_url='login')
@user_passes_test(is_staff_admin)
@never_cache
def qr_exit_validation(request):
    """
    Handles QR scan for vehicle EXIT validation only.
    Detects active EntryLog and marks vehicle as departed automatically.
    Returns JSON suitable for AJAX use.
    """
    if request.method != "POST":
        return JsonResponse({
            "status": "error",
            "message": "Invalid request method. Use POST."
        })

    qr_code = request.POST.get("qr_code", "").strip()
    if not qr_code:
        return JsonResponse({
            "status": "error",
            "message": "QR code is missing or invalid."
        })

    try:
        vehicle = Vehicle.objects.filter(qr_value__iexact=qr_code).first()
        if not vehicle:
            return JsonResponse({
                "status": "error",
                "message": "❌ No vehicle found for this QR code."
            })

        # 🟩 Check if there’s an active entry
        active_log = EntryLog.objects.filter(vehicle=vehicle, is_active=True).first()
        if not active_log:
            return JsonResponse({
                "status": "error",
                "message": f"⚠️ Vehicle '{vehicle.license_plate}' is not currently inside the terminal."
            })

        # ✅ Mark as departed
        active_log.is_active = False
        active_log.departed_at = timezone.now()
        active_log.message = (
            f"Vehicle '{vehicle.license_plate}' departed at "
            f"{timezone.localtime(active_log.departed_at).strftime('%I:%M %p')}."
        )
        active_log.save(update_fields=["is_active", "departed_at", "message"])

        return JsonResponse({
            "status": "success",
            "message": f"✅ Vehicle '{vehicle.license_plate}' successfully departed at "
                       f"{timezone.localtime(active_log.departed_at).strftime('%I:%M %p')}."
        })

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        })


@login_required(login_url='login')
@user_passes_test(is_staff_admin)
@never_cache
def qr_exit_page(request):
    """Renders the separate page for Exit QR Scanning."""
    return render(request, "terminal/qr_exit_validation.html")



@login_required(login_url='login')
@user_passes_test(is_staff_admin)
@never_cache
def system_settings(request):
    """Allows admin/staff_admin to view and update terminal-wide configurations."""
    settings = SystemSettings.get_solo()

    class SettingsForm(forms.ModelForm):
        class Meta:
            model = SystemSettings
            fields = [
                'terminal_fee',
                'min_deposit_amount',
                'entry_cooldown_minutes',
                'departure_duration_minutes',  # 🟢 NEW FIELD
                'theme_preference',
            ]
            widgets = {
                'terminal_fee': forms.NumberInput(attrs={
                    'class': 'form-control',
                    'min': '0', 'step': '0.01',
                    'placeholder': 'Enter terminal entry fee (₱)',
                }),
                'min_deposit_amount': forms.NumberInput(attrs={
                    'class': 'form-control',
                    'min': '0', 'step': '0.01',
                    'placeholder': 'Enter minimum deposit required (₱)',
                }),
                'entry_cooldown_minutes': forms.NumberInput(attrs={
                    'class': 'form-control',
                    'min': '1', 'step': '1',
                    'placeholder': 'Entry cooldown (minutes)',
                }),
                'departure_duration_minutes': forms.NumberInput(attrs={
                    'class': 'form-control',
                    'min': '1', 'step': '1',
                    'placeholder': 'Default stay duration (minutes)',
                }),
                'theme_preference': forms.Select(attrs={'class': 'form-select'}),
            }

    form = SettingsForm(request.POST or None, instance=settings)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "✅ System settings updated successfully!")
            return redirect('terminal:system_settings')
        else:
            messages.error(request, "❌ Please correct the errors below.")

    return render(request, "terminal/system_settings.html", {"form": form})



# 🟩 STEP 3.3.1: AJAX endpoint to mark a vehicle as departed
@login_required(login_url='login')
@user_passes_test(is_staff_admin)
@never_cache
def mark_departed(request, entry_id):
    """
    Marks a vehicle entry as departed (is_active=False, sets departed_at timestamp).
    Used by AJAX button on Terminal Queue page.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request method."})

    try:
        log = get_object_or_404(EntryLog, id=entry_id, is_active=True)
        log.is_active = False
        log.departed_at = timezone.now()
        log.save(update_fields=["is_active", "departed_at"])
        return JsonResponse({
            "success": True,
            "message": f"✅ Vehicle '{log.vehicle.license_plate}' marked as departed."
        })
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error: {str(e)}"})



# 🟢 STEP 3.6: Adjust Departure Time (AJAX)
@login_required(login_url='login')
@user_passes_test(is_staff_admin)
@never_cache
def update_departure_time(request, entry_id):
    """
    Allows staff to manually adjust a vehicle's departure time from the manage queue page.
    """
    from django.utils.dateparse import parse_datetime
    import json

    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request method."})

    try:
        log = get_object_or_404(EntryLog, id=entry_id, is_active=True)

        data = json.loads(request.body)
        new_time_str = data.get("departure_time", "")

        if not new_time_str:
            return JsonResponse({"success": False, "message": "No departure time provided."})

        new_time = parse_datetime(new_time_str)
        if not new_time:
            return JsonResponse({"success": False, "message": "Invalid datetime format."})

        # ✅ Save new departure time
        log.departed_at = timezone.make_aware(new_time)
        log.save(update_fields=["departed_at"])

        return JsonResponse({
            "success": True,
            "message": f"Departure time for '{log.vehicle.license_plate}' updated successfully.",
            "new_departure": timezone.localtime(log.departed_at).strftime("%I:%M %p")
        })

    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error: {str(e)}"})







# 🟩 STEP 3.4.1: Queue History View
@login_required(login_url='login')
@user_passes_test(is_staff_admin)
@never_cache
def queue_history(request):
    """
    Displays all vehicle entry logs (active and departed)
    with filters for status, date range, and export option.
    """
    logs = EntryLog.objects.select_related('vehicle', 'staff').order_by('-created_at')

    # 🟢 Filters
    status_filter = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    if status_filter:
        logs = logs.filter(status=status_filter)

    if start_date:
        logs = logs.filter(created_at__date__gte=start_date)

    if end_date:
        logs = logs.filter(created_at__date__lte=end_date)

    # 🟣 CSV Export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="queue_history.csv"'
        writer = csv.writer(response)
        writer.writerow(['Plate', 'Driver', 'Status', 'Fee', 'Staff', 'Entry Time'])

        for log in logs:
            writer.writerow([
                getattr(log.vehicle, 'license_plate', 'N/A'),
                f"{log.vehicle.assigned_driver.first_name} {log.vehicle.assigned_driver.last_name}" if log.vehicle and log.vehicle.assigned_driver else "N/A",
                log.status.title(),
                f"₱{log.fee_charged}",
                log.staff.username if log.staff else "N/A",
                timezone.localtime(log.created_at).strftime("%Y-%m-%d %H:%M"),
            ])
        return response

    context = {
        "logs": logs[:200],  # display limit
        "status_filter": status_filter,
        "start_date": start_date,
        "end_date": end_date,
    }
    return render(request, "terminal/queue_history.html", context)