from django.urls import path
from . import views

app_name = 'passenger'

urlpatterns = [
    path('home/', views.home, name='home'),
    path('announcement/', views.announcement, name='announcement'),
    path('', views.public_queue_view, name='public_queue'),
    path('data/', views.public_queue_data, name='public_queue_data'),
    path('contact/', views.contact, name='contact'),
]
