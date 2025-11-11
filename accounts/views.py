from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.contrib.auth import logout, authenticate, login
from .models import CustomUser
from .forms import CustomUserCreationForm, CustomUserEditForm
from vehicles.models import Driver, Vehicle
from terminal.models import EntryLog

# ===============================
# ✅ ROLE HELPERS
# ===============================
def is_admin(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, 'role', '') == 'admin')


def is_staff_admin(user):
    return user.is_authenticated and (user.is_staff or getattr(user, 'role', '') == 'staff_admin')


# ===============================
# ✅ LOGIN VIEW (Secure & Role-Based)
# ===============================
@never_cache
def login_view(request):
    # Only redirect if user is already logged in
    if request.user.is_authenticated:
        if is_admin(request.user):
            return redirect('accounts:admin_dashboard')
        elif is_staff_admin(request.user):
            return redirect('accounts:staff_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)

            # Session expires on browser close
            request.session.set_expiry(0)
            request.session['role'] = getattr(user, 'role', '')
            request.session['secure_login'] = True
            request.session.modified = True

            if is_admin(user):
                return redirect('accounts:admin_dashboard')
            elif is_staff_admin(user):
                return redirect('accounts:staff_dashboard')
            else:
                messages.error(request, "Access denied: unauthorized role.")
                logout(request)
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'accounts/login.html')


# ===============================
# ✅ LOGOUT VIEW
# ===============================
@never_cache
def logout_view(request):
    logout(request)
    request.session.flush()
    messages.success(request, "You have been logged out successfully.")
    return redirect('accounts:login')


# ===============================
# ✅ MANAGE USERS
# ===============================
@login_required(login_url='login')
@user_passes_test(lambda u: is_admin(u) or is_staff_admin(u))
@never_cache
def manage_users(request):
    """Allow Admins and Staff Admins to view the user list."""
    if is_admin(request.user):
        users = CustomUser.objects.exclude(username=request.user.username).order_by('username')
    else:
        users = CustomUser.objects.filter(role='staff_admin').exclude(username=request.user.username)
    return render(request, 'accounts/manage_users.html', {'users': users})


# ===============================
# ✅ CREATE USER
# ===============================
@login_required(login_url='login')
@user_passes_test(lambda u: is_admin(u) or is_staff_admin(u))
@never_cache
def create_user(request):
    """Admins can create Admin and Staff Admin accounts; Staff Admins only Staff Admin."""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, user=request.user)
        if form.is_valid():
            new_user = form.save()
            messages.success(request, f"✅ New {new_user.role.replace('_', ' ').title()} '{new_user.username}' created.")
            return redirect('accounts:manage_users')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomUserCreationForm(user=request.user)
    return render(request, 'accounts/create_user.html', {'form': form})


# ===============================
# ✅ EDIT USER
# ===============================
@login_required(login_url='login')
@user_passes_test(lambda u: is_admin(u) or is_staff_admin(u))
@never_cache
def edit_user(request, user_id):
    user_obj = get_object_or_404(CustomUser, id=user_id)

    if is_staff_admin(request.user) and user_obj.role == 'admin':
        messages.error(request, "Access denied: You cannot edit Admin accounts.")
        return redirect('accounts:manage_users')

    form = CustomUserEditForm(request.POST or None, instance=user_obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"✅ User '{user_obj.username}' updated successfully.")
        return redirect('accounts:manage_users')

    return render(request, 'accounts/edit_user.html', {'form': form, 'user_obj': user_obj})


# ===============================
# ✅ DELETE USER
# ===============================
@login_required(login_url='login')
@user_passes_test(is_admin)
@never_cache
def delete_user(request, user_id):
    user_obj = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        user_obj.delete()
        messages.success(request, f"✅ User '{user_obj.username}' deleted successfully.")
        return redirect('accounts:manage_users')

    context = {
        'item_name': user_obj.username,
        'item_type': 'User Account',
        'cancel_url': '/accounts/manage-users/',
    }
    return render(request, 'includes/confirm_delete.html', context)


# ===============================
# ✅ ADMIN DASHBOARD
# ===============================
@login_required(login_url='/accounts/terminal-access/')
@user_passes_test(is_admin)
@never_cache
def admin_dashboard_view(request):
    from reports.models import Profit
    from django.db.models import Sum
    from datetime import datetime, timedelta
    from django.utils import timezone
    # Import QueueHistory from vehicles so the admin view and vehicles app are consistent
    try:
        from vehicles.models import QueueHistory
    except Exception:
        QueueHistory = None

    total_drivers = Driver.objects.count()
    total_vehicles = Vehicle.objects.count()

    # Prefer QueueHistory if available; fall back to EntryLog if your terminal app still uses it.
    total_queue = 0
    if QueueHistory is not None:
        total_queue = QueueHistory.objects.filter().count()
    else:
        try:
            total_queue = EntryLog.objects.filter(status=EntryLog.STATUS_SUCCESS).count()
        except Exception:
            total_queue = 0

    total_profit = Profit.objects.aggregate(Sum('amount'))['amount__sum'] or 0

    # Chart data for last 7 days (server-side)
    today = timezone.now().date()
    last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    chart_labels = [d.strftime("%b %d") for d in last_7_days]
    chart_data = []

    for day in last_7_days:
        start = timezone.make_aware(datetime.combine(day, datetime.min.time()))
        end = timezone.make_aware(datetime.combine(day, datetime.max.time()))
        day_total = Profit.objects.filter(date_recorded__range=[start, end]).aggregate(Sum('amount'))['amount__sum'] or 0
        chart_data.append(float(day_total))

    context = {
        'total_drivers': total_drivers,
        'total_vehicles': total_vehicles,
        'total_queue': total_queue,
        'total_profit': total_profit,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'now': timezone.now(),
    }
    return render(request, 'accounts/admin_dashboard.html', context)



# ===============================
# ✅ STAFF DASHBOARD
# ===============================
@login_required(login_url='/accounts/terminal-access/')
@user_passes_test(is_staff_admin)
@never_cache
def staff_dashboard_view(request):
    total_drivers = Driver.objects.count()
    total_vehicles = Vehicle.objects.count()
    total_queue = EntryLog.objects.filter(status=EntryLog.STATUS_SUCCESS).count()

    context = {
        'total_drivers': total_drivers,
        'total_vehicles': total_vehicles,
        'total_queue': total_queue,
    }
    return render(request, 'accounts/staff_dashboard.html', context)
