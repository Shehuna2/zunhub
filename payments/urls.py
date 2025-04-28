from django.urls import path
from . import views

urlpatterns = [
    path('deposit/', views.deposit, name='deposit'),
    path('deposit/callback/', views.deposit_callback, name='deposit_callback'),
    path('webhook/', views.flutterwave_webhook, name='flutterwave_webhook'),
    path('ping/', views.healthcheck_ping, name='healthcheck_ping'), 
]