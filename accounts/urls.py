from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from payments.views import flutterwave_webhook
from . import views

urlpatterns = [
    path('payments/webhook/', csrf_exempt(flutterwave_webhook), name='flutterwave-webhook'),
    path("update-bank-details/", views.update_bank_details, name="update_bank_details"),
    path("accounts/edit-profile/", views.edit_profile, name="edit_profile"),
    path('profile/', views.profile_view, name='profile'),
    path('accounts/register/', views.register, name='register'),
    path('accounts/login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
]