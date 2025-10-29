# terminal/urls.py
from django.urls import path
from . import views

app_name = 'terminal'

urlpatterns = [
    # ✅ Staff deposit page
    path('deposit-menu/', views.deposit_menu, name='deposit_menu'),

    # ✅ Terminal queue page
    path('queue/', views.terminal_queue, name='terminal_queue'),
]
