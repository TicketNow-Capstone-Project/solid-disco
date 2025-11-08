from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache
from django.http import JsonResponse, HttpResponse
from vehicles.models import Vehicle, Wallet, Driver, Deposit
from .models import EntryLog, SystemSettings
from decimal import Decimal
from django import forms
from django.contrib import messages
from django.utils import timezone
import csv
from datetime import timedelta
from accounts.utils import is_staff_admin_or_admin, is_admin   # ✅ imported shared role checks


# ===============================
#   DEPOSIT MENU (Role-based)
# ===============================
@login_required(login_url='login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def deposit_menu(request):
    """Admin sees history with filters; staff can record new deposits."""
    settings = SystemSettings.get_solo()
    min_deposit = settings.min_deposit_amount
    user = request.user

    # 🟩 Base Query
    deposits = Deposit.objects.select_related('wallet__vehicle__assigned_driver').order_by('-created_at')

    # 🧠 If user is ADMIN → show history & filters
    if user.role == "admin":
        start_date = request.GET.get("start_date", "")
        end_date = request.GET.get("end_date", "")
        vehicle_plate = request.GET.get("vehicle_plate", "")

        if start_date:
            deposits = deposits.filter(created_at__date__gte=start_date)
        if end_date:
            deposits = deposits.filter(created_at__date__lte=end_date)
        if vehicle_plate:
            deposits = deposits.filter(wallet__vehicle__license_plate__icontains=vehicle_plate)

        context = {
            "role": "admin",
            "deposits": deposits[:200],
            "start_date": start_date,
            "end_date": end_date,
            "vehicle_plate": vehicle_plate,
            "min_deposit": min_deposit,
        }
        return render(request, "terminal/deposit_menu.html", context)

    # 🟦 If user is STAFF ADMIN → show form + recent deposits
    drivers_with_vehicles = (
        Driver.objects.filter(vehicles__isnull=False)
        .distinct()
        .order_by('last_name', 'first_name')
    )

    recent_deposits = deposits[:10]

    if request.method == "POST":
        vehicle_id = request.POST.get("vehicle_id")
        amount_str = request.POST.get("amount", "").strip()

        if not vehicle_id or not amount_str:
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

        vehicle = Vehicle.objects.filter(id=vehicle_id).first()
        if not vehicle:
            messages.error(request, "❌ Vehicle not found.")
            return redirect('terminal:deposit_menu')

        wallet, _ = Wallet.objects.get_or_create(vehicle=vehicle)
        Deposit.objects.create(wallet=wallet, amount=amount)

        messages.success(request, f"✅ Successfully deposited ₱{amount} to {vehicle.license_plate}.")
        return redirect('terminal:deposit_menu')

    context = {
        "role": "staff_admin",
        "drivers": drivers_with_vehicles,
        "recent_deposits": recent_deposits,
        "context_message": "" if drivers_with_vehicles.exists() else
            "No registered drivers with vehicles found. Please register a vehicle first.",
        "min_deposit": min_deposit,
    }
    return render(request, "terminal/deposit_menu.html", context)



# ===============================
#   QUEUE & SIMPLE QUEUE
# ===============================
@login_required(login_url='login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def terminal_queue(request):
    return render(request, 'terminal/terminal_queue.html')


@login_required(login_url='login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def queue_data(request):
    """AJAX endpoint for live queue refresh."""
    logs = (
        EntryLog.objects.filter(status=EntryLog.STATUS_SUCCESS, is_active=True)
        .select_related("vehicle__assigned_driver", "staff")
        .order_by("-created_at")[:20]
    )
    data = []
    for log in logs:
        v = log.vehicle
        d = v.assigned_driver if v else None
        data.append({
            "id": log.id,
            "vehicle_plate": getattr(v, "license_plate", "N/A") if v else "—",
            "vehicle_name": getattr(v, "vehicle_name", "—") if v else "—",
            "driver_name": f"{d.first_name} {d.last_name}" if d else "—",
            "fee": float(log.fee_charged),
            "staff": log.staff.username if log.staff else "—",
            "time": log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return JsonResponse({"entries": data})


@login_required(login_url='login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def simple_queue_view(request):
    """Display-only queue for TV display."""
    settings = SystemSettings.get_solo()
    duration = getattr(settings, "departure_duration_minutes", 30)
    logs = (
        EntryLog.objects.filter(is_active=True, status=EntryLog.STATUS_SUCCESS)
        .select_related("vehicle__assigned_driver")
        .order_by("-created_at")
    )

    queue = []
    for log in logs:
        v = log.vehicle
        d = v.assigned_driver if v else None
        departure_time = log.created_at + timedelta(minutes=duration)
        queue.append({
            "plate": getattr(v, "license_plate", "N/A"),
            "driver": f"{d.first_name} {d.last_name}" if d else "N/A",
            "entry_time": timezone.localtime(log.created_at).strftime("%I:%M %p"),
            "departure_time": timezone.localtime(departure_time).strftime("%I:%M %p"),
        })

    context = {"queue": queue, "stay_duration": duration, "now": timezone.localtime(timezone.now())}
    return render(request, "terminal/simple_queue.html", context)


# ===============================
#   MANAGE QUEUE
# ===============================
@login_required(login_url='login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def manage_queue(request):
    settings = SystemSettings.get_solo()
    duration = getattr(settings, "departure_duration_minutes", 30)
    logs = (
        EntryLog.objects.filter(is_active=True, status=EntryLog.STATUS_SUCCESS)
        .select_related("vehicle__assigned_driver", "staff")
        .order_by("-created_at")
    )

    queue = []
    for log in logs:
        v = log.vehicle
        d = v.assigned_driver if v else None
        departure_time = log.created_at + timedelta(minutes=duration)
        queue.append({
            "id": log.id,
            "plate": getattr(v, "license_plate", "N/A"),
            "driver": f"{d.first_name} {d.last_name}" if d else "N/A",
            "entry_time": timezone.localtime(log.created_at).strftime("%I:%M %p"),
            "departure_time": timezone.localtime(departure_time).strftime("%I:%M %p"),
            "staff": log.staff.username if log.staff else "—",
        })

    return render(request, "terminal/manage_queue.html", {"queue": queue, "stay_duration": duration})


# ===============================
#   QR ENTRY / EXIT
# ===============================
@login_required(login_url='login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def qr_scan_entry(request):
    """Handles QR scan for both entry & departure validation."""
    settings = SystemSettings.get_solo()
    entry_fee = settings.terminal_fee
    cooldown_minutes = settings.entry_cooldown_minutes
    min_deposit = settings.min_deposit_amount

    if request.method == "POST":
        qr_code = request.POST.get("qr_code", "").strip()
        if not qr_code:
            return JsonResponse({"status": "error", "message": "QR code is empty."})
        staff_user = request.user

        try:
            vehicle = Vehicle.objects.filter(qr_value__iexact=qr_code).first()
            if not vehicle:
                return JsonResponse({"status": "error", "message": "Invalid QR."})

            wallet = Wallet.objects.filter(vehicle=vehicle).first()
            if not wallet:
                return JsonResponse({"status": "error", "message": "No wallet found."})

            from datetime import timedelta, timezone, datetime
            now = datetime.now(timezone.utc)
            active_log = EntryLog.objects.filter(vehicle=vehicle, is_active=True).first()

            # DEPARTURE
            if active_log:
                active_log.is_active = False
                active_log.departed_at = timezone.now()
                active_log.message = f"Vehicle '{vehicle.license_plate}' departed."
                active_log.save(update_fields=["is_active", "departed_at", "message"])
                return JsonResponse({"status": "success", "message": f"✅ {vehicle.license_plate} departed."})

            # ENTRY
            recent_entry = EntryLog.objects.filter(vehicle=vehicle, status=EntryLog.STATUS_SUCCESS).order_by("-created_at").first()
            if recent_entry and (now - recent_entry.created_at) < timedelta(minutes=cooldown_minutes):
                return JsonResponse({"status": "error", "message": "⏳ Please wait before re-entry."})

            if wallet.balance < min_deposit:
                return JsonResponse({"status": "error", "message": f"⚠️ Minimum ₱{min_deposit} required."})

            if wallet.balance >= entry_fee:
                wallet.balance -= entry_fee
                wallet.save()
                EntryLog.objects.create(vehicle=vehicle, staff=staff_user, fee_charged=entry_fee,
                                        status=EntryLog.STATUS_SUCCESS,
                                        message=f"Vehicle '{vehicle.license_plate}' entered terminal.")
                return JsonResponse({"status": "success", "message": f"🚗 {vehicle.license_plate} entered terminal."})
            else:
                EntryLog.objects.create(vehicle=vehicle, staff=staff_user, fee_charged=entry_fee,
                                        status=EntryLog.STATUS_INSUFFICIENT,
                                        message=f"Insufficient balance for '{vehicle.license_plate}'.")
                return JsonResponse({"status": "error", "message": "❌ Insufficient balance."})

        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Unexpected error: {str(e)}"})

    context = {"terminal_fee": entry_fee, "min_deposit": min_deposit, "cooldown": cooldown_minutes}
    return render(request, "terminal/qr_scan_entry.html", context)


@login_required(login_url='login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def qr_exit_validation(request):
    """Handles QR scan for exit validation only."""
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request method."})

    qr_code = request.POST.get("qr_code", "").strip()
    if not qr_code:
        return JsonResponse({"status": "error", "message": "QR missing."})

    try:
        vehicle = Vehicle.objects.filter(qr_value__iexact=qr_code).first()
        if not vehicle:
            return JsonResponse({"status": "error", "message": "❌ No vehicle found."})

        active_log = EntryLog.objects.filter(vehicle=vehicle, is_active=True).first()
        if not active_log:
            return JsonResponse({"status": "error", "message": f"⚠️ {vehicle.license_plate} not inside terminal."})

        active_log.is_active = False
        active_log.departed_at = timezone.now()
        active_log.save(update_fields=["is_active", "departed_at"])
        return JsonResponse({"status": "success", "message": f"✅ {vehicle.license_plate} departed."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})


@login_required(login_url='login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def qr_exit_page(request):
    return render(request, "terminal/qr_exit_validation.html")


# ===============================
#   SYSTEM SETTINGS (Admin only)
# ===============================
@login_required(login_url='login')
@user_passes_test(is_admin)
@never_cache
def system_settings(request):
    """Admin-only configuration page with seat capacity limits."""
    settings = SystemSettings.get_solo()

    class SettingsForm(forms.ModelForm):
        class Meta:
            model = SystemSettings
            fields = [
                'terminal_fee',
                'min_deposit_amount',
                'entry_cooldown_minutes',
                'departure_duration_minutes',
                # 🟢 Added new fields
                'jeepney_max_seats',
                'van_max_seats',
                'bus_max_seats',
                'theme_preference',
            ]
            widgets = {
                'terminal_fee': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
                'min_deposit_amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
                'entry_cooldown_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
                'departure_duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
                'jeepney_max_seats': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
                'van_max_seats': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
                'bus_max_seats': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
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


# ===============================
#   MARK DEPARTED / UPDATE TIME / HISTORY
# ===============================
@login_required(login_url='login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def mark_departed(request, entry_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request."})
    try:
        log = get_object_or_404(EntryLog, id=entry_id, is_active=True)
        log.is_active = False
        log.departed_at = timezone.now()
        log.save(update_fields=["is_active", "departed_at"])
        return JsonResponse({"success": True, "message": f"✅ {log.vehicle.license_plate} marked departed."})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})


@login_required(login_url='login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def update_departure_time(request, entry_id):
    from django.utils.dateparse import parse_datetime
    import json
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request."})
    try:
        log = get_object_or_404(EntryLog, id=entry_id, is_active=True)
        data = json.loads(request.body)
        new_time = parse_datetime(data.get("departure_time", ""))
        if not new_time:
            return JsonResponse({"success": False, "message": "Invalid datetime."})
        log.departed_at = timezone.make_aware(new_time)
        log.save(update_fields=["departed_at"])
        return JsonResponse({"success": True, "message": f"Updated departure for {log.vehicle.license_plate}."})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})


@login_required(login_url='login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def queue_history(request):
    logs = EntryLog.objects.select_related('vehicle', 'staff').order_by('-created_at')
    status_filter = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    if status_filter:
        logs = logs.filter(status=status_filter)
    if start_date:
        logs = logs.filter(created_at__date__gte=start_date)
    if end_date:
        logs = logs.filter(created_at__date__lte=end_date)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="queue_history.csv"'
        writer = csv.writer(response)
        writer.writerow(['Plate', 'Driver', 'Status', 'Fee', 'Staff', 'Entry Time'])
        for log in logs:
            writer.writerow([
                getattr(log.vehicle, 'license_plate', 'N/A'),
                f"{log.vehicle.assigned_driver.first_name} {log.vehicle.assigned_driver.last_name}"
                if log.vehicle and log.vehicle.assigned_driver else "N/A",
                log.status.title(),
                f"₱{log.fee_charged}",
                log.staff.username if log.staff else "N/A",
                timezone.localtime(log.created_at).strftime("%Y-%m-%d %H:%M"),
            ])
        return response

    return render(request, "terminal/queue_history.html",
                  {"logs": logs[:200], "status_filter": status_filter,
                   "start_date": start_date, "end_date": end_date})
