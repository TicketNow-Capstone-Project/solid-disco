from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache
from django.http import JsonResponse
from vehicles.models import Vehicle, Wallet

# 🔐 Helper: Check if user is staff
def is_staff_admin(user):
    return user.is_authenticated and (user.is_staff or getattr(user, 'role', '') == 'staff_admin')

# ✅ Deposit Menu View
@login_required(login_url='login')
@user_passes_test(is_staff_admin)
@never_cache
def deposit_menu(request):
    return render(request, 'terminal/deposit_menu.html')

# ✅ Terminal Queue View (Optional placeholder)
@login_required(login_url='login')
@user_passes_test(is_staff_admin)
@never_cache
def terminal_queue(request):
    return render(request, 'terminal/terminal_queue.html')

# 🟩 STEP 2: QR Scan Entry Validation
@login_required(login_url='login')
@user_passes_test(is_staff_admin)
@never_cache
def qr_scan_entry(request):
    """
    Handles QR scan or manual input from staff to validate vehicle entry.
    Deducts entry fee from the vehicle's wallet if sufficient balance.
    """
    if request.method == "POST":
        qr_code = request.POST.get("qr_code", "").strip()

        if not qr_code:
            return JsonResponse({"status": "error", "message": "QR code cannot be empty."})

        try:
            # Look up the vehicle by its QR code value
            vehicle = get_object_or_404(Vehicle, qr_code=qr_code)
            wallet = Wallet.objects.get(vehicle=vehicle)
            entry_fee = 10.00  # You can adjust this as needed

            if wallet.balance >= entry_fee:
                wallet.balance -= entry_fee
                wallet.save()
                return JsonResponse({
                    "status": "success",
                    "message": f"Vehicle '{vehicle.plate_number}' entry validated. ₱{entry_fee} deducted."
                })
            else:
                return JsonResponse({
                    "status": "error",
                    "message": f"Insufficient balance for vehicle '{vehicle.plate_number}'."
                })

        except Vehicle.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Invalid QR code. Vehicle not found."})
        except Wallet.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Wallet not found for this vehicle."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Unexpected error: {str(e)}"})

    # GET request → load the scan page
    return render(request, "terminal/qr_scan_entry.html")
