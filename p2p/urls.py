from django.urls import path
from . import views

urlpatterns = [
    path('accounts/register/', views.register, name='register'),
    path('accounts/login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    # path('wallet/', views.wallet_dashboard, name='wallet'),
    # path('wallet/funding/', views.merchant_list, name='funding'),
    # path('wallet/deposit/', views.deposit, name='deposit'),
    # path('wallet/withdraw/', views.withdraw, name='withdraw'),
    path('merchants/', views.merchant_list, name='merchant_list'),
    path('marketplace/', views.marketplace, name='marketplace'),
    path('order/<int:order_id>/', views.order_details, name='order_details'),
    path('orders/buyer/', views.buyer_orders, name='buyer_orders'),
    path('orders/merchant/', views.merchant_orders, name='merchant_orders'),
    path("update-bank-details/", views.update_bank_details, name="update_bank_details"),
    
    path('order/create/<int:offer_id>/', views.create_order, name='create_order'),    
    path('order/<int:order_id>/mark-as-paid/', views.mark_as_paid, name='mark_as_paid'),
    path('order/confirm/<int:order_id>/', views.confirm_payment, name='confirm_payment'),
    path("order/dispute/create/<int:order_id>/", views.create_dispute, name="create_dispute"),
    path("dispute/cancel/<int:dispute_id>/", views.cancel_dispute, name="cancel_dispute"),
    path("dispute/track/<int:dispute_id>/", views.track_dispute, name="track_dispute"),
    path("disputes/", views.dispute_list, name="dispute_list"),
]
