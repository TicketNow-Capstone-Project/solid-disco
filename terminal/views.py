from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache
from django.http import JsonResponse, HttpResponse
from vehicles.models import Vehicle, Wallet, Driver, Deposit, Route
from .models import EntryLog, SystemSettings
from decimal import Decimal
from django import forms
from django.contrib import messages
from django.utils import timezone
import csv
from datetime import timedelta
from accounts.utils import is_staff_admin_or_admin, is_admin   # ✅ imported shared role checks
from pytz import timezone as pytz_timezone

# ---- Deposit menu (unchanged) ----
@login_required(login_url='login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def deposit_menu(request):
    settings = SystemSettings.get_solo()
    min_deposit = settings.min_deposit_amount
    user = request.user
    deposits = Deposit.objects.select_related('wallet__vehicle__assigned_driver').order_by('-created_at')

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
        context = {"role":"admin","deposits":deposits[:200],"start_date":start_date,"end_date":end_date,"vehicle_plate":vehicle_plate,"min_deposit":min_deposit}
        return render(request, "terminal/deposit_menu.html", context)

    drivers_with_vehicles = Driver.objects.filter(vehicles__isnull=False).distinct().order_by('last_name','first_name')
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

    context = {"role":"staff_admin","drivers":drivers_with_vehicles,"recent_deposits":recent_deposits,"context_message":"" if drivers_with_vehicles.exists() else "No registered drivers with vehicles found. Please register a vehicle first.","min_deposit":min_deposit}
    return render(request, "terminal/deposit_menu.html", context)


# ===============================
#   TERMINAL QUEUE PAGE WRAPPER
# ===============================
@login_required(login_url='login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def terminal_queue(request):
    """Render the main terminal queue page (the page which will poll queue-data)."""
    return render(request, "terminal/terminal_queue.html")


# ===============================
#   QUEUE DATA (AJAX endpoint)
# ===============================
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

    ph_tz = pytz_timezone("Asia/Manila")
    data = []
    for log in logs:
        v = log.vehicle
        d = v.assigned_driver if v else None
        # convert created_at to local time for display
        entry_local = timezone.localtime(log.created_at, ph_tz)
        data.append({
            "id": log.id,
            "vehicle_plate": getattr(v, "license_plate", "N/A") if v else "—",
            "vehicle_name": getattr(v, "vehicle_name", "—") if v else "—",
            "driver_name": f"{d.first_name} {d.last_name}" if d else "—",
            "fee": float(log.fee_charged),
            "staff": log.staff.username if log.staff else "—",
            "time": entry_local.strftime("%Y-%m-%d %I:%M %p"),
        })
    return JsonResponse({"entries": data})


# ===============================
#   SIMPLE QUEUE (TV)
# ===============================
@login_required(login_url='login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def simple_queue_view(request):
    settings = SystemSettings.get_solo()
    duration = getattr(settings, "departure_duration_minutes", 30)
    logs = EntryLog.objects.filter(is_active=True, status=EntryLog.STATUS_SUCCESS).select_related("vehicle__assigned_driver").order_by("-created_at")
    ph_tz = pytz_timezone("Asia/Manila")
    queue = []
    for log in logs:
        v = log.vehicle
        d = v.assigned_driver if v else None
        departure_time = log.created_at + timedelta(minutes=duration)
        queue.append({
            "plate": getattr(v, "license_plate", "N/A"),
            "driver": f"{d.first_name} {d.last_name}" if d else "N/A",
            "entry_time": timezone.localtime(log.created_at, ph_tz).strftime("%I:%M %p"),
            "departure_time": timezone.localtime(departure_time, ph_tz).strftime("%I:%M %p"),
        })
    context = {"queue": queue, "stay_duration": duration, "now": timezone.localtime(timezone.now(), ph_tz)}
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
    logs = EntryLog.objects.filter(is_active=True, status=EntryLog.STATUS_SUCCESS).select_related("vehicle__assigned_driver","staff").order_by("-created_at")
    ph_tz = pytz_timezone("Asia/Manila")
    queue = []
    for log in logs:
        v = log.vehicle
        d = v.assigned_driver if v else None
        departure_time = log.created_at + timedelta(minutes=duration)
        queue.append({
            "id": log.id,
            "plate": getattr(v, "license_plate", "N/A"),
            "driver": f"{d.first_name} {d.last_name}" if d else "N/A",
            "entry_time": timezone.localtime(log.created_at, ph_tz).strftime("%I:%M %p"),
            "departure_time": timezone.localtime(departure_time, ph_tz).strftime("%I:%M %p"),
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
    """Handles QR scan for both entry & departure validation with live balance feedback."""
    settings = SystemSettings.get_solo()
    entry_fee = settings.terminal_fee
    cooldown_minutes = settings.entry_cooldown_minutes
    min_deposit = settings.min_deposit_amount

    if request.method == "POST":
        qr_code = request.POST.get("qr_code", "").strip()
        if not qr_code:
            return JsonResponse({
                "status": "error",
                "message": "QR code is empty.",
                "balance": None
            })

        staff_user = request.user

        try:
            # 🔍 Validate vehicle
            vehicle = Vehicle.objects.filter(qr_value__iexact=qr_code).first()
            if not vehicle:
                return JsonResponse({
                    "status": "error",
                    "message": "❌ Invalid QR code.",
                    "balance": None
                })

            # 🏦 Get or create wallet
            wallet, _ = Wallet.objects.get_or_create(vehicle=vehicle)

            from datetime import timedelta, timezone, datetime
            now = datetime.now(timezone.utc)

            # 🚗 Check if vehicle already inside terminal
            active_log = EntryLog.objects.filter(vehicle=vehicle, is_active=True).first()

            # ========================
            # 🔁 DEPARTURE LOGIC
            # ========================
            if active_log:
                active_log.is_active = False
                active_log.departed_at = timezone.now()
                active_log.message = f"Vehicle '{vehicle.license_plate}' departed."
                active_log.save(update_fields=["is_active", "departed_at", "message"])

                return JsonResponse({
                    "status": "success",
                    "message": f"✅ {vehicle.license_plate} departed successfully.",
                    "balance": float(wallet.balance)
                })

            # ========================
            # 🚘 ENTRY LOGIC
            # ========================
            recent_entry = EntryLog.objects.filter(
                vehicle=vehicle,
                status=EntryLog.STATUS_SUCCESS
            ).order_by("-created_at").first()

            if recent_entry and (now - recent_entry.created_at) < timedelta(minutes=cooldown_minutes):
                return JsonResponse({
                    "status": "error",
                    "message": "⏳ Please wait before re-entry.",
                    "balance": float(wallet.balance)
                })

            if wallet.balance < min_deposit:
                return JsonResponse({
                    "status": "error",
                    "message": f"⚠️ Minimum ₱{min_deposit} required before entry.",
                    "balance": float(wallet.balance)
                })

            if wallet.balance >= entry_fee:
                wallet.balance -= entry_fee
                wallet.save()

                EntryLog.objects.create(
                    vehicle=vehicle,
                    staff=staff_user,
                    fee_charged=entry_fee,
                    status=EntryLog.STATUS_SUCCESS,
                    message=f"Vehicle '{vehicle.license_plate}' entered terminal."
                )

                return JsonResponse({
                    "status": "success",
                    "message": f"🚗 {vehicle.license_plate} entered terminal.",
                    "balance": float(wallet.balance)
                })
            else:
                EntryLog.objects.create(
                    vehicle=vehicle,
                    staff=staff_user,
                    fee_charged=entry_fee,
                    status=EntryLog.STATUS_INSUFFICIENT,
                    message=f"Insufficient balance for '{vehicle.license_plate}'."
                )

                return JsonResponse({
                    "status": "error",
                    "message": f"❌ Insufficient balance for {vehicle.license_plate}.",
                    "balance": float(wallet.balance)
                })

        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "balance": None
            })

    # GET request → render scan page
    context = {
        "terminal_fee": entry_fee,
        "min_deposit": min_deposit,
        "cooldown": cooldown_minutes,
    }
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


@login_required(login_url='login')
@user_passes_test(is_admin)
@never_cache
def manage_routes(request):
    """Admin-only page for adding, editing, and deleting routes."""
    routes = Route.objects.all().order_by('origin', 'destination')

    if request.method == "POST":
        action = request.POST.get("action")
        route_id = request.POST.get("route_id")
        name = request.POST.get("name", "").strip()
        origin = request.POST.get("origin", "").strip()
        destination = request.POST.get("destination", "").strip()
        base_fare = request.POST.get("base_fare", "").strip()
        active = bool(request.POST.get("active"))

        if not origin or not destination:
            messages.error(request, "⚠️ Both origin and destination are required.")
            return redirect("terminal:manage_routes")

        try:
            base_fare = Decimal(base_fare) if base_fare else 0.00
        except:
            base_fare = 0.00

        if action == "add":
            Route.objects.create(
                name=name or f"{origin} - {destination}",
                origin=origin,
                destination=destination,
                base_fare=base_fare,
                active=active,
            )
            messages.success(request, f"✅ Route {origin} → {destination} added successfully!")

        elif action == "edit" and route_id:
            route = get_object_or_404(Route, id=route_id)
            route.name = name or f"{origin} - {destination}"
            route.origin = origin
            route.destination = destination
            route.base_fare = base_fare
            route.active = active
            route.save()
            messages.success(request, f"✅ Route {origin} → {destination} updated!")

        elif action == "delete" and route_id:
            route = get_object_or_404(Route, id=route_id)
            route.delete()
            messages.success(request, f"🗑️ Route deleted successfully.")

        return redirect("terminal:manage_routes")

    return render(request, "terminal/manage_routes.html", {"routes": routes})


# ===============================
#   AJAX ADD DEPOSIT (New)
# ===============================
from django.views.decorators.csrf import csrf_exempt

@login_required(login_url='login')
@user_passes_test(is_staff_admin_or_admin)
@csrf_exempt
def ajax_add_deposit(request):
    """AJAX-based deposit submission (no page reload)."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'})

    vehicle_id = request.POST.get('vehicle_id')
    amount = request.POST.get('amount')

    if not vehicle_id or not amount:
        return JsonResponse({'success': False, 'message': 'Missing fields.'})

    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
        wallet, _ = Wallet.objects.get_or_create(vehicle=vehicle)
        amt = Decimal(amount)

        if amt <= 0:
            return JsonResponse({'success': False, 'message': 'Amount must be greater than zero.'})

        deposit = Deposit.objects.create(wallet=wallet, amount=amt)

        return JsonResponse({
            'success': True,
            'message': f"✅ Deposit of ₱{amt} for {vehicle.license_plate} recorded!",
            'deposit': {
                'reference': deposit.reference_number,
                'driver': f"{vehicle.assigned_driver.last_name}, {vehicle.assigned_driver.first_name}",
                'vehicle': vehicle.license_plate,
                'amount': float(deposit.amount),
                'date': deposit.created_at.strftime("%b %d, %Y %I:%M %p")
            }
        })
    except Vehicle.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Vehicle not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required(login_url='login')
@user_passes_test(is_staff_admin_or_admin)
@csrf_exempt
def ajax_get_wallet_balance(request):
    """Return current wallet balance for a selected vehicle."""
    vehicle_id = request.GET.get('vehicle_id')
    if not vehicle_id:
        return JsonResponse({'success': False, 'message': 'Vehicle ID missing.'})

    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
        wallet, _ = Wallet.objects.get_or_create(vehicle=vehicle)
        return JsonResponse({
            'success': True,
            'balance': float(wallet.balance),
            'vehicle': vehicle.license_plate
        })
    except Vehicle.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Vehicle not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
