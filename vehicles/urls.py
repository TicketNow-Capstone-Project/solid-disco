# vehicles/urls.py
from django.urls import path
from . import views

app_name = 'vehicles'

urlpatterns = [
    # ✅ Dedicated registration pages
    path('register-driver/', views.register_driver, name='register_driver'),
    path('register-vehicle/', views.register_vehicle, name='register_vehicle'),

    # ✅ QR / printable page (staff-only)
    path('vehicle/<int:vehicle_id>/qr/', views.vehicle_qr_view, name='vehicle_qr'),

    # ✅ AJAX / backend helpers
    path('ocr-process/', views.ocr_process, name='ocr_process'),
    path('ajax-register-driver/', views.ajax_register_driver, name='ajax_register_driver'),
    path('ajax-register-vehicle/', views.ajax_register_vehicle, name='ajax_register_vehicle'),
    path('get-wallet-balance/<int:driver_id>/', views.get_wallet_balance, name='get_wallet_balance'),
    path('ajax-deposit/', views.ajax_deposit, name='ajax_deposit'),
]
