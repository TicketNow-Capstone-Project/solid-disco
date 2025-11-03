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


# ✅ Deposit Menu View (Improved + Safe Handling)
@login_required(login_url='login')
@user_passes_test(is_staff_admin)
@never_cache
def deposit_menu(request):
    """
    Allows staff to select a driver (only those with registered vehicles),
    view wallet balance, and record deposits.
    """

    settings = SystemSettings.get_solo()
    min_deposit = settings.min_deposit_amount



    # 🟩 Only drivers who have at least one registered vehicle
    drivers_with_vehicles = (
        Driver.objects
        .filter(vehicles__isnull=False)
        .distinct()
        .order_by('last_name', 'first_name')
    )

    # 🟩 Fetch the 10 most recent deposits
    recent_deposits = (
        Deposit.objects
        .select_related('wallet__vehicle__assigned_driver')
        .order_by('-created_at')[:10]
    )

    # 🧠 Optional: Context info for debugging if no drivers found
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





# 🟩 STEP 2.2: QR Scan Entry Validation + Enhanced Error Feedback
@login_required(login_url='login')
@user_passes_test(is_staff_admin)
@never_cache
def qr_scan_entry(request):
    """
    Handles QR scans for vehicle entry validation.
    Deducts terminal fee if balance is sufficient and cooldown has passed.
    Prevents re-entry within the configured cooldown.
    """
    # 🧩 Load dynamic settings (defaults if missing)
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
            print("Scanned QR:", qr_code)
            if not vehicle:
                return JsonResponse({
                    "status": "error",
                    "message": "No vehicle found for this QR code. Please make sure it's valid."
                })

            # ⏱ Prevent re-entry within cooldown
            from datetime import timedelta, timezone, datetime
            now = datetime.now(timezone.utc)
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

            wallet = Wallet.objects.filter(vehicle=vehicle).first()
            if not wallet:
                return JsonResponse({
                    "status": "error",
                    "message": "No wallet found for this vehicle. Please deposit funds first."
                })

            # 💰 Check minimum deposit requirement
            if wallet.balance < min_deposit:
                return JsonResponse({
                    "status": "error",
                    "message": f"⚠️ Minimum deposit of ₱{min_deposit} required before entry. "
                               "Please add funds at the deposit counter."
                })

            # ✅ Check if sufficient for entry fee
            if wallet.balance >= entry_fee:
                wallet.balance -= entry_fee
                wallet.save()

                EntryLog.objects.create(
                    vehicle=vehicle,
                    staff=staff_user,
                    fee_charged=entry_fee,
                    status=EntryLog.STATUS_SUCCESS,
                    message=f"Vehicle '{vehicle.license_plate}' validated. ₱{entry_fee} deducted."
                )

                return JsonResponse({
                    "status": "success",
                    "message": f"✅ Vehicle '{vehicle.license_plate}' validated successfully! ₱{entry_fee} deducted."
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

    # 🟦 Display current settings at top of page
    context = {
        "terminal_fee": entry_fee,
        "min_deposit": min_deposit,
        "cooldown": cooldown_minutes,
    }
    return render(request, "terminal/qr_scan_entry.html", context)



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