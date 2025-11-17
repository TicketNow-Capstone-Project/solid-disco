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
from django.db.models import Q
from django.utils.text import slugify

# Default delete window (minutes) for cleanup of old logs (tweakable)
DEFAULT_DELETE_AFTER_MINUTES = 10


def _apply_auto_close_and_cleanup(now=None, delete_after_minutes=None):
    """
    Centralized maintenance for entry logs:
    - Auto-close (is_active=False + departed_at set) any entry where created_at + departure_duration <= now.
    - Delete old departed/non-active entries older than delete_after_minutes.
    This uses the admin-configured SystemSettings.departure_duration_minutes as the authoritative rule.
    """
    now = now or timezone.now()
    settings = SystemSettings.get_solo()
    departure_duration = getattr(settings, "departure_duration_minutes", 30)

    # 1) Auto-close active entries where created_at + departure_duration <= now
    # Compute cutoff = now - departure_duration
    cutoff = now - timedelta(minutes=int(departure_duration))
    # Only affect entries that are still marked active and were created at or before cutoff
    active_to_close = EntryLog.objects.filter(is_active=True, created_at__lte=cutoff)
    if active_to_close.exists():
        active_to_close.update(is_active=False, departed_at=now)

    # 2) Delete departed/non-active entries older than delete_after_minutes
    delete_after_minutes = delete_after_minutes if delete_after_minutes is not None else DEFAULT_DELETE_AFTER_MINUTES
    delete_cutoff = now - timedelta(minutes=int(delete_after_minutes))
    old_qs = EntryLog.objects.filter(created_at__lt=delete_cutoff).filter(Q(is_active=False) | Q(departed_at__isnull=False))
    if old_qs.exists():
        old_qs.delete()


# ---- Deposit menu (unchanged) ----
@login_required(login_url='accounts:login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def deposit_menu(request):
    settings = SystemSettings.get_solo()
    min_deposit = settings.min_deposit_amount
    user = request.user

    # Base queryset
    deposits = Deposit.objects.select_related(
        'wallet__vehicle__assigned_driver'
    ).order_by('-created_at')

    # ================================
    #          ADMIN VIEW
    # ================================
    if user.role == "admin":
        start_date = request.GET.get("start_date", "")
        end_date = request.GET.get("end_date", "")
        vehicle_plate = request.GET.get("vehicle_plate", "")

        # 🟢 If NO filters → show TODAY by default
        if not start_date and not end_date and not vehicle_plate:
            today = timezone.localdate()
            deposits = deposits.filter(created_at__date=today)
            start_date = today.isoformat()
            end_date = today.isoformat()
        else:
            # 🟡 Apply filters only if provided
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

    # ================================
    #          STAFF VIEW
    # ================================
    drivers_with_vehicles = Driver.objects.filter(
        vehicles__isnull=False
    ).distinct().order_by('last_name', 'first_name')

    # 🟢 Staff always sees TODAY'S deposits by default
    today = timezone.localdate()
    recent_deposits = deposits.filter(
        created_at__date=today
    )[:10]

    # -------------------------------
    # Handle POST deposit submission
    # -------------------------------
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
        "context_message": "" if drivers_with_vehicles.exists() else "No registered drivers with vehicles found. Please register a vehicle first.",
        "min_deposit": min_deposit,
    }
    return render(request, "terminal/deposit_menu.html", context)


# ===============================
#   DEPOSIT ANALYTICS (Admin)
# ===============================
@login_required(login_url='accounts:login')
@user_passes_test(is_admin)
@never_cache
def deposit_analytics(request):
    """Admin-only analytics dashboard for deposits."""
    from django.db.models import Sum, Count
    from django.db.models.functions import TruncDate

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    deposits = (
        Deposit.objects
        .select_related("wallet__vehicle__assigned_driver")
        .order_by("-created_at")
    )

    # Apply filters
    if start_date:
        deposits = deposits.filter(created_at__date__gte=start_date)
    if end_date:
        deposits = deposits.filter(created_at__date__lte=end_date)

    # Summary Metrics
    total_amount = deposits.aggregate(Sum("amount"))["amount__sum"] or 0
    total_transactions = deposits.count()
    unique_vehicles = deposits.values("wallet__vehicle").distinct().count()
    unique_drivers = deposits.values("wallet__vehicle__assigned_driver").distinct().count()

    # Top 5 Drivers
    top_drivers = (
        deposits.values("wallet__vehicle__assigned_driver__first_name",
                        "wallet__vehicle__assigned_driver__last_name")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:5]
    )

    # Daily Deposits Chart
    daily_data = (
        deposits.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Sum("amount"))
        .order_by("day")
    )

    chart_labels = [d["day"].strftime("%b %d") for d in daily_data]
    chart_data = [float(d["total"]) for d in daily_data]

    context = {
        "total_amount": total_amount,
        "total_transactions": total_transactions,
        "unique_vehicles": unique_vehicles,
        "unique_drivers": unique_drivers,
        "top_drivers": top_drivers,
        "chart_labels": chart_labels,
        "chart_data": chart_data,
        "start_date": start_date or "",
        "end_date": end_date or "",
    }
    return render(request, "terminal/deposit_analytics.html", context)


# ===============================
#   DEPOSIT VS REVENUE COMPARISON (Admin)
# ===============================
@login_required(login_url='accounts:login')
@user_passes_test(is_admin)
@never_cache
def deposit_vs_revenue(request):
    """Compare total deposits vs terminal fees collected (EntryLog fees) per day."""
    from django.db.models import Sum
    from django.db.models.functions import TruncDate

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    deposits = Deposit.objects.all()
    logs = EntryLog.objects.filter(status=EntryLog.STATUS_SUCCESS)

    # Apply filters
    if start_date:
        deposits = deposits.filter(created_at__date__gte=start_date)
        logs = logs.filter(created_at__date__gte=start_date)
    if end_date:
        deposits = deposits.filter(created_at__date__lte=end_date)
        logs = logs.filter(created_at__date__lte=end_date)

    # Aggregate per day
    from collections import defaultdict
    daily_totals = defaultdict(lambda: {"deposit": 0, "revenue": 0})

    for d in (
        deposits.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Sum("amount"))
    ):
        daily_totals[d["day"]]["deposit"] = float(d["total"])

    for l in (
        logs.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Sum("fee_charged"))
    ):
        daily_totals[l["day"]]["revenue"] = float(l["total"])

    # Sort and prepare for chart
    sorted_days = sorted(daily_totals.keys())
    chart_labels = [d.strftime("%b %d") for d in sorted_days]
    deposits_data = [daily_totals[d]["deposit"] for d in sorted_days]
    revenue_data = [daily_totals[d]["revenue"] for d in sorted_days]

    context = {
        "chart_labels": chart_labels,
        "deposits_data": deposits_data,
        "revenue_data": revenue_data,
        "start_date": start_date or "",
        "end_date": end_date or "",
    }
    return render(request, "terminal/deposit_vs_revenue.html", context)




# ===============================
#   TERMINAL QUEUE PAGE WRAPPER
# ===============================
@login_required(login_url='accounts:login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def terminal_queue(request):
    """Render the main terminal queue page (the page which will poll queue-data)."""
    # ensure auto-close/cleanup runs for admin pages too
    _apply_auto_close_and_cleanup()
    return render(request, "terminal/terminal_queue.html")


@login_required(login_url='accounts:login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def tv_display_view(request, route_slug=None):
    """
    Terminal TV Display
    - Correct route filtering using slug
    - Groups active vehicles by route
    """

    # Run cleanup for consistency
    _apply_auto_close_and_cleanup()

    # Local timezone
    ph_tz = pytz_timezone("Asia/Manila")

    settings = SystemSettings.get_solo()
    duration = getattr(settings, "departure_duration_minutes", 30)

    # All available routes (for dropdown)
    all_routes = Route.objects.filter(active=True).order_by("origin", "destination")

    # Build slug → name mapping
    route_map = {slugify(r.name): r.name for r in all_routes}

    selected_route_name = None

    # If slug is provided, convert to real route name
    if route_slug:
        route_slug = route_slug.lower().strip("/")
        selected_route_name = route_map.get(route_slug)

    # Base queryset of active entries
    logs = (
        EntryLog.objects.filter(is_active=True, status=EntryLog.STATUS_SUCCESS)
        .select_related("vehicle__assigned_driver", "vehicle__route")
        .order_by("vehicle__route__origin", "vehicle__route__destination", "created_at")
    )

    # Apply route filter
    if selected_route_name:
        logs = logs.filter(vehicle__route__name=selected_route_name)

    # Group output
    grouped_routes = {}
    for log in logs:
        v = log.vehicle
        d = v.assigned_driver if v else None
        route_name = v.route.name if v and v.route else "Unassigned Route"

        departure_time = log.created_at + timedelta(minutes=duration)

        grouped_routes.setdefault(route_name, []).append({
            "plate": getattr(v, "license_plate", "N/A"),
            "driver": f"{d.first_name} {d.last_name}" if d else "N/A",
            "entry_time": timezone.localtime(log.created_at, ph_tz).strftime("%I:%M %p"),
            "departure_time": timezone.localtime(departure_time, ph_tz).strftime("%I:%M %p"),
        })

    context = {
        "grouped_routes": grouped_routes,
        "stay_duration": duration,
        "all_routes": all_routes,
        "selected_route": selected_route_name or "All Routes",
    }

    return render(request, "terminal/tv_display.html", context)

# ===============================
#   QUEUE DATA (AJAX endpoint)
# ===============================
@login_required(login_url='accounts:login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def queue_data(request):
    """AJAX endpoint for live queue refresh."""
    # maintenance
    _apply_auto_close_and_cleanup()

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
@login_required(login_url='accounts:login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def simple_queue_view(request):
    # maintenance
    _apply_auto_close_and_cleanup()

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
@login_required(login_url='accounts:login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def manage_queue(request):
    # maintenance
    _apply_auto_close_and_cleanup()

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
@login_required(login_url='accounts:login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def qr_scan_entry(request):
    """Handles QR scan for both entry & departure validation with live balance feedback."""
    # Run maintenance on entry routes too so state is consistent when scanning
    _apply_auto_close_and_cleanup()

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


@login_required(login_url='accounts:login')
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


@login_required(login_url='accounts:login')
@user_passes_test(is_staff_admin_or_admin)
@never_cache
def qr_exit_page(request):
    return render(request, "terminal/qr_exit_validation.html")


# ===============================
#   SYSTEM SETTINGS (Admin only)
# ===============================
@login_required(login_url='accounts:login')
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
@login_required(login_url='accounts:login')
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


@login_required(login_url='accounts:login')
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


@login_required(login_url='accounts:login')
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


@login_required(login_url='accounts:login')
@user_passes_test(is_admin)
@never_cache
def manage_routes(request):
    """Admin-only page for managing routes and viewing analytics."""
    from django.db.models import Count, Sum
    from .models import EntryLog

    # --- ROUTE CRUD HANDLING ---
    if request.method == "POST":
        action = request.POST.get("action")
        route_id = request.POST.get("route_id")
        name = request.POST.get("name", "").strip()
        origin = request.POST.get("origin", "").strip()
        destination = request.POST.get("destination", "").strip()
        base_fare = request.POST.get("base_fare", "").strip()
        active = bool(request.POST.get("active"))

        # Validation
        if not origin or not destination:
            messages.error(request, "⚠️ Both origin and destination are required.")
            return redirect("terminal:manage_routes")

        try:
            base_fare = Decimal(base_fare) if base_fare else Decimal("0.00")
        except Exception:
            base_fare = Decimal("0.00")

        # Prevent duplicate routes
        existing = Route.objects.filter(
            origin__iexact=origin,
            destination__iexact=destination
        ).exclude(id=route_id).exists()
        if existing:
            messages.error(request, f"⚠️ Route {origin} → {destination} already exists.")
            return redirect("terminal:manage_routes")

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
            messages.success(request, f"✅ Route {origin} → {destination} updated successfully!")

        elif action == "delete" and route_id:
            route = get_object_or_404(Route, id=route_id)
            route_name = f"{route.origin} → {route.destination}"
            route.delete()
            messages.success(request, f"🗑️ Route {route_name} deleted successfully!")

        else:
            messages.warning(request, "⚠️ Invalid action or missing route ID.")

        return redirect("terminal:manage_routes")

    # --- ANALYTICS SECTION ---
    routes = Route.objects.all().order_by('origin', 'destination')

    route_stats = (
        EntryLog.objects
        .filter(vehicle__route__isnull=False)
        .values('vehicle__route__id', 'vehicle__route__origin', 'vehicle__route__destination')
        .annotate(
            total_trips=Count('id'),
            total_fees=Sum('fee_charged')
        )
        .order_by('-total_trips')
    )

    total_trips = sum(item['total_trips'] for item in route_stats)
    total_fees = sum(item['total_fees'] or 0 for item in route_stats)
    active_routes = routes.filter(active=True).count()
    top_route = route_stats[0] if route_stats else None

    # --- Chart.js Data ---
    chart_labels = [f"{r['vehicle__route__origin']} → {r['vehicle__route__destination']}" for r in route_stats]
    chart_data = [r['total_trips'] for r in route_stats]

    context = {
        "routes": routes,
        "total_trips": total_trips,
        "total_fees": total_fees,
        "active_routes": active_routes,
        "top_route": top_route,
        "chart_labels": chart_labels,
        "chart_data": chart_data,
    }

    return render(request, "terminal/manage_routes.html", context)



# ===============================
#   AJAX ADD DEPOSIT (New)
# ===============================
from django.views.decorators.csrf import csrf_exempt

@login_required(login_url='accounts:login')
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


@login_required(login_url='accounts:login')
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
