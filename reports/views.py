# reports/views.py
from django.shortcuts import render
from django.db.models import Sum
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal
import pytz
from accounts.utils import is_admin
from vehicles.models import Deposit
from terminal.models import EntryLog, SystemSettings
from .models import Profit


# ============================================================
# 📊 REPORTS HOME
# ============================================================
@login_required(login_url='login')
@user_passes_test(is_admin)
def reports_home(request):
    """Display overview links to all reports."""
    return render(request, 'reports/reports_home.html')



# ============================================================
# 💰 DEPOSIT ANALYTICS
# ============================================================
@login_required(login_url='login')
@user_passes_test(is_admin)
def deposit_analytics(request):
    """Show 7-day deposit trend and top vehicles by total deposit."""
    now = timezone.localtime()
    start_date = now - timedelta(days=6)  # Last 7 days (including today)

    # 🟦 Compute daily totals for the past 7 days
    labels = []
    daily_totals = []
    for i in range(7):
        day = (start_date + timedelta(days=i)).date()
        total = (
            Deposit.objects.filter(created_at__date=day)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        labels.append(day.strftime("%b %d"))
        daily_totals.append(float(total))

    total_deposits = sum(daily_totals)

    # 🟨 Top 5 vehicles by total deposit
    top_vehicles = (
        Deposit.objects.values("wallet__vehicle__license_plate")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:5]
    )

    context = {
        "labels": labels,
        "daily_totals": daily_totals,
        "total_deposits": total_deposits,
        "top_vehicles": top_vehicles,
    }
    return render(request, "reports/deposit_analytics.html", context)



# ============================================================
# 💵 DEPOSIT VS REVENUE
# ============================================================
@login_required(login_url='login')
@user_passes_test(is_admin)
def deposit_vs_revenue(request):
    """Compare total deposits vs total terminal fees per day."""
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    # Default range → last 7 days
    if not start_date or not end_date:
        end_date = timezone.localdate()
        start_date = end_date - timedelta(days=6)

    else:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    chart_labels, deposits_data, revenue_data = [], [], []

    for i in range((end_date - start_date).days + 1):
        day = start_date + timedelta(days=i)
        chart_labels.append(day.strftime("%b %d"))

        daily_deposit = (
            Deposit.objects.filter(created_at__date=day)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        deposits_data.append(float(daily_deposit))

        daily_revenue = (
            EntryLog.objects.filter(created_at__date=day, status="success")
            .aggregate(total=Sum("fee_charged"))["total"]
            or Decimal("0.00")
        )
        revenue_data.append(float(daily_revenue))

    context = {
        "chart_labels": chart_labels,
        "deposits_data": deposits_data,
        "revenue_data": revenue_data,
        "start_date": start_date,
        "end_date": end_date,
    }
    return render(request, "reports/deposit_vs_revenue.html", context)


# ============================================================
# 📈 PROFIT TREND (Profit Report)
# ============================================================
@login_required(login_url='login')
@user_passes_test(is_admin)
def profit_report_view(request):
    """Visual profit trend and total profit summary."""
    profits = Profit.objects.all().order_by("-date_recorded")
    total = profits.aggregate(Sum("amount"))["amount__sum"] or 0

    # --- Optional: Date Range Filtering ---
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            # Properly handle timezone conversion
            local_tz = timezone.get_current_timezone()
            end_dt = timezone.make_aware(
                datetime.combine(end_dt, datetime.max.time()), 
                timezone=local_tz
            )
            start_dt = timezone.make_aware(
                datetime.combine(start_dt, datetime.min.time()), 
                timezone=local_tz
            )
            
            profits = profits.filter(date_recorded__range=[start_dt, end_dt])
            total = profits.aggregate(Sum("amount"))["amount__sum"] or 0
        except ValueError:
            pass

    # Prepare data for chart with proper timezone handling
    chart_labels, profit_values = [], []
    for p in profits.order_by("date_recorded"):
        local_date = timezone.localtime(p.date_recorded)
        chart_labels.append(local_date.strftime("%b %d"))
        profit_values.append(float(p.amount))

    context = {
        "profits": profits,
        "total": total,
        "profit_labels": chart_labels,
        "profit_values": profit_values,
        "start_date": start_date,
        "end_date": end_date,
    }
    return render(request, "reports/profit_report.html", context)
