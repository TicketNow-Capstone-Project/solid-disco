from django.urls import path
from . import views

urlpatterns = [
    #path('register-driver/', views.driver_registration, name='driver_registration'),
    #path('ocr-process/', views.ocr_process, name='ocr_process'),

    path('register/', views.vehicle_registration, name='vehicle_registration'),

]