from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache
from django.db.models import Sum
from .forms import DriverRegistrationForm, CustomUserCreationForm, CustomUserEditForm
from .models import CustomUser
from vehicles.models import Driver, Vehicle
from terminal.models import TerminalQueue
from reports.models import Profit


# ✅ Import related models for dashboard statistics
try:
    from vehicles.models import Vehicle
except ImportError:
    Vehicle = None

try:
    from drivers.models import Driver
except ImportError:
    Driver = None

try:
    from terminal.models import TerminalQueue
except ImportError:
    TerminalQueue = None

try:
    from reports.models import Profit
except ImportError:
    Profit = None


# ===============================
# 🔐 ROLE CHECK HELPERS
# ===============================
def is_admin(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, 'role', '') == 'admin')


def is_staff_admin(user):
    return user.is_authenticated and (user.is_staff or getattr(user, 'role', '') == 'staff_admin')


# ===============================
# 🔑 LOGIN & LOGOUT
# ===============================
def login_view(request):
    if not request.user.is_authenticated:
        request.session.flush()

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if is_admin(user):
                login(request, user)
                request.session['role'] = 'admin'
                return redirect('admin_dashboard')
            elif is_staff_admin(user):
                login(request, user)
                request.session['role'] = 'staff_admin'
                return redirect('staff_dashboard')
            else:
                messages.error(request, "Access denied. Only admins and staff can access this system.")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    request.session.flush()
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')


# ===============================
# 🧑‍💼 ADMIN DASHBOARD
# ===============================
@login_required(login_url='login')
@user_passes_test(is_admin)
@never_cache
def admin_dashboard_view(request):
    # Defensive fallbacks if models not imported yet
    total_drivers = Driver.objects.count() if Driver else 0
    total_vehicles = Vehicle.objects.count() if Vehicle else 0
    total_queue = TerminalQueue.objects.count() if TerminalQueue else 0
    total_profit = Profit.objects.aggregate(total=Sum('amount'))['total'] if Profit else 0

    context = {
        'total_drivers': total_drivers or 0,
        'total_vehicles': total_vehicles or 0,
        'total_queue': total_queue or 0,
        'total_profit': total_profit or 0,
    }
    return render(request, 'accounts/admin_dashboard.html', context)


# ===============================
# 🧑‍🔧 STAFF DASHBOARD
# ===============================
@login_required(login_url='login')
@user_passes_test(is_staff_admin)
@never_cache
def staff_dashboard_view(request):
    total_drivers = Driver.objects.count() if Driver else 0
    total_vehicles = Vehicle.objects.count() if Vehicle else 0

    context = {
        'total_drivers': total_drivers,
        'total_vehicles': total_vehicles,
    }
    return render(request, 'accounts/staff_dashboard.html', context)


# ===============================
# 🧾 DRIVER REGISTRATION (Staff)
# ===============================
@login_required(login_url='login')
@user_passes_test(is_staff_admin)
def driver_registration(request):
    if request.method == 'POST':
        form = DriverRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Driver registered successfully!")
            return redirect('driver_registration_success')
    else:
        form = DriverRegistrationForm()
    return render(request, 'driver_registration.html', {'form': form})


@login_required(login_url='login')
@user_passes_test(is_staff_admin)
def driver_registration_success(request):
    return render(request, 'registration_success.html', {
        'message': 'Driver registration submitted successfully!'
    })


# ===============================
# 👥 USER MANAGEMENT (Admin Only)
# ===============================
@login_required(login_url='login')
@user_passes_test(is_admin)
def manage_users_view(request):
    users = CustomUser.objects.exclude(role='driver')
    return render(request, 'accounts/manage_users.html', {'users': users})


@login_required(login_url='login')
@user_passes_test(is_admin)
def create_user_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            if user.role == 'driver':
                messages.error(request, 'Cannot create a driver account here.')
                return redirect('create_user')
            user.save()
            messages.success(request, f'{user.role.capitalize()} "{user.username}" created successfully!')
            return redirect('manage_users')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/create_user.html', {'form': form})


@login_required(login_url='login')
@user_passes_test(is_admin)
def edit_user_view(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    form = CustomUserEditForm(request.POST or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Account "{user.username}" updated successfully!')
        return redirect('manage_users')
    return render(request, 'accounts/edit_user.html', {'form': form, 'user_obj': user})


@login_required(login_url='login')
@user_passes_test(is_admin)
def delete_user_view(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'Account "{username}" has been deleted.')
        return redirect('manage_users')
    return render(request, 'accounts/delete_user.html', {'user_obj': user})
