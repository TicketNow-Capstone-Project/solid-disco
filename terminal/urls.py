from django.urls import path
from . import views

app_name = 'terminal'

urlpatterns = [
    path('deposit-menu/', views.deposit_menu, name='deposit_menu'),
    path('queue/', views.terminal_queue, name='terminal_queue'),
    path('queue-data/', views.queue_data, name='queue_data'),
    path('manage-queue/', views.manage_queue, name='manage_queue'),
    path('simple-queue/', views.simple_queue_view, name='simple_queue_view'),
    path('qr-scan-entry/', views.qr_scan_entry, name='qr_scan_entry'),
    path('qr-exit/', views.qr_exit_validation, name='qr_exit_validation'),
    path('qr-exit-page/', views.qr_exit_page, name='qr_exit_page'),
    path('queue-history/', views.queue_history, name='queue_history'),
    path('manage-routes/', views.manage_routes, name='manage_routes'),
    path('system-settings/', views.system_settings, name='system_settings'),
    path('mark-departed/<int:entry_id>/', views.mark_departed, name='mark_departed'),
    path('update-departure/<int:entry_id>/', views.update_departure_time, name='update_departure_time'),
    path('ajax-add-deposit/', views.ajax_add_deposit, name='ajax_add_deposit'),
    path('ajax-get-wallet-balance/', views.ajax_get_wallet_balance, name='ajax_get_wallet_balance'),

]
