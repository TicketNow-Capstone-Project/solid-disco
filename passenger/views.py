# passenger/views.py
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from terminal.models import EntryLog, SystemSettings
from vehicles.models import Vehicle, Route
from django.http import JsonResponse

def public_queue_view(request):
    """
    Passenger Public View
    - Shows all active and recently departed vehicles (last 10 minutes)
    - Calculates departure time (entry + waiting time)
    - Adds route filtering and countdown-ready data
    """
    # ✅ System setting for departure duration (default: 30 minutes)
    settings = SystemSettings.get_solo()
    departure_duration = getattr(settings, "departure_duration_minutes", 30)

    now = timezone.now()
    route_filter = request.GET.get("route", "all")

    # ✅ Collect all routes for dropdown filter
    routes = Route.objects.filter(active=True).order_by("origin", "destination")

    # ✅ Active and recently departed vehicles (keep visible for 10 minutes)
    ten_mins_ago = now - timedelta(minutes=10)
    queue_entries = (
        EntryLog.objects.select_related("vehicle", "vehicle__assigned_driver", "vehicle__route")
        .filter(
            status=EntryLog.STATUS_SUCCESS,
            created_at__gte=ten_mins_ago - timedelta(minutes=departure_duration),  # only recent records
        )
        .order_by("created_at")
    )

    # ✅ Filter by selected route (if not "all")
    if route_filter != "all":
        queue_entries = queue_entries.filter(vehicle__route_id=route_filter)

    # ✅ Process each record: mark boarding/departed and compute departure time
    enriched_entries = []
    for q in queue_entries:
        v = q.vehicle
        departure_time = q.created_at + timedelta(minutes=departure_duration)
        is_boarding = q.is_active  # inside terminal
        is_departed_recently = not q.is_active and q.departed_at and (now - q.departed_at <= timedelta(minutes=10))

        if is_boarding or is_departed_recently:
            enriched_entries.append({
                "vehicle": v,
                "is_active": is_boarding,
                "departed_at": departure_time,
            })

    context = {
        "queue_entries": enriched_entries,
        "routes": routes,
        "selected_route": route_filter,
    }

    return render(request, "passenger/public_queue.html", context)


def public_queue_data(request):
    """AJAX endpoint that returns live queue data for smooth refresh."""
    from datetime import timedelta
    from django.utils import timezone
    from terminal.models import EntryLog, SystemSettings
    from vehicles.models import Route

    settings = SystemSettings.get_solo()
    departure_duration = getattr(settings, "departure_duration_minutes", 30)
    now = timezone.now()

    ten_mins_ago = now - timedelta(minutes=10)
    route_filter = request.GET.get("route", "all")

    queue_entries = (
        EntryLog.objects.select_related("vehicle", "vehicle__assigned_driver", "vehicle__route")
        .filter(
            status=EntryLog.STATUS_SUCCESS,
            created_at__gte=ten_mins_ago - timedelta(minutes=departure_duration),
        )
        .order_by("created_at")
    )

    if route_filter != "all":
        queue_entries = queue_entries.filter(vehicle__route_id=route_filter)

    data = []
    for q in queue_entries:
        v = q.vehicle
        departure_time = q.created_at + timedelta(minutes=departure_duration)
        is_boarding = q.is_active
        is_departed_recently = not q.is_active and q.departed_at and (now - q.departed_at <= timedelta(minutes=10))
        if is_boarding or is_departed_recently:
            data.append({
                "plate": v.license_plate,
                "driver": f"{v.assigned_driver.first_name} {v.assigned_driver.last_name}" if v.assigned_driver else "—",
                "route": f"{v.route.origin} → {v.route.destination}" if v.route else "—",
                "status": "Boarding" if is_boarding else "Departed",
                "departure": departure_time.strftime("%Y-%m-%d %H:%M:%S"),
            })

    return JsonResponse({"entries": data})