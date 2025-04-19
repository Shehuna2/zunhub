from django.urls import path
from . import views

urlpatterns = [
    # path('accounts/register/', views.register, name='register'),
    # path('accounts/login/', views.user_login, name='login'),
    # path('logout/', views.user_logout, name='logout'),
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
    # path("update-bank-details/", views.update_bank_details, name="update_bank_details"),
    
    path('p2p/sell-offer/create/', views.create_sell_offer, name='create_sell_offer'), # Merchant create p2p offer
    path('p2p/order/create/<int:offer_id>/', views.create_order, name='create_order'), # Buyer create order   
    path('p2p/order/<int:order_id>/mark-as-paid/', views.mark_as_paid, name='mark_as_paid'), # Buyer mark order as paid
    path('p2p/order/confirm/<int:order_id>/', views.confirm_payment, name='confirm_payment'), # Merchant confirm payment
    path("p2p/order/dispute/create/<int:order_id>/", views.create_dispute, name="create_dispute"), # Buyer create dispute
    path("p2p/dispute/cancel/<int:dispute_id>/", views.cancel_dispute, name="cancel_dispute"), # Buyer cancel dispute
    path("p2p/dispute/track/<int:dispute_id>/", views.track_dispute, name="track_dispute"), # Buyer track dispute
    path("p2p/disputes/", views.dispute_list, name="dispute_list"), # Merchant view disputes
]
