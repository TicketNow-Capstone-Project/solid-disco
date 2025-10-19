from django.urls import path
from . import views

urlpatterns = [
    path('profit-report/', views.profit_report_view, name='profit_report'),
]
