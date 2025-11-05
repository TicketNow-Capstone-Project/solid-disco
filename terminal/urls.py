# terminal/urls.py
from django.urls import path
from . import views

app_name = 'terminal'

urlpatterns = [
    # ✅ Staff deposit page
    path('deposit-menu/', views.deposit_menu, name='deposit_menu'),

    # ✅ Terminal queue page (main live page)
    path('queue/', views.terminal_queue, name='terminal_queue'),

    # ✅ QR Scan Entry page (Step 2)
    path('qr-scan-entry/', views.qr_scan_entry, name='qr_scan_entry'),

    # 🆕 AJAX endpoint for auto-refresh queue (Step 3.5)
    path('queue-data/', views.queue_data, name='queue_data'),

    # 🟩 Step 3.3: Mark as Departed (AJAX)
    path('mark-departed/<int:entry_id>/', views.mark_departed, name='mark_departed'),

    path('update-departure/<int:entry_id>/', views.update_departure_time, name='update_departure_time'),


    # 📜 Queue History page
    path('queue-history/', views.queue_history, name='queue_history'),

    # 🟢 Simple Queue (TV Display)
    path('simple-queue/', views.simple_queue_view, name='simple_queue_view'),

    # 🆕 Manage Queue (Staff Control Panel)
    path('manage-queue/', views.manage_queue, name='manage_queue'),

    # ⚙️ Admin-only System Settings
    path('system-settings/', views.system_settings, name='system_settings'),
]
