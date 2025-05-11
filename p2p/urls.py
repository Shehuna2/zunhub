from django.urls import path
from . import views

urlpatterns = [

    path('', views.dashboard, name='dashboard'),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),


    # path('merchants/', views.merchant_list, name='merchant_list'),
    path('marketplace/', views.marketplace, name='marketplace'),
    path('order/<int:order_id>/', views.order_details, name='order_details'),
    path('orders/buyer/', views.buyer_orders, name='buyer_orders'),
    path('orders/merchant/', views.merchant_orders, name='merchant_orders'),
    
    path('p2p/sell-offer/create/', views.create_sell_offer, name='create_sell_offer'), # Merchant create p2p offer
    path('p2p/order/create/<int:offer_id>/', views.create_order, name='create_order'), # Buyer create order   
    path('p2p/order/<int:order_id>/mark-as-paid/', views.mark_as_paid, name='mark_as_paid'), # Buyer mark order as paid
    path('p2p/order/confirm/<int:order_id>/', views.release_fund, name='release_fund'), # Merchant confirm payment
    path("p2p/order/dispute/create/<int:order_id>/", views.create_dispute, name="create_dispute"), # Buyer create dispute
    path("p2p/dispute/cancel/<int:dispute_id>/", views.cancel_dispute, name="cancel_dispute"), # Buyer cancel dispute
    path("p2p/dispute/track/<int:dispute_id>/", views.track_dispute, name="track_dispute"), # Buyer track dispute
    path("p2p/disputes/", views.dispute_list, name="dispute_list"), # Merchant view disputes

    path('p2p/buy-offer/create/', views.create_buy_offer, name='create_buy_offer'),
    path('p2p/buy-offers/',        views.buy_offers_marketplace, name='buy_offers_marketplace'),
    path('p2p/sell-order/create/<int:offer_id>/', views.create_sell_order, name='create_sell_order'),
    path('p2p/sell-order/confirm/<int:order_id>/', views.merchant_confirm_sell, name='merchant_confirm_sell'),
    path('p2p/sell-order/<int:order_id>/', views.sell_order_details, name='sell_order_details'), 

    path('p2p/sell-order/<int:order_id>/confirm-payment/',views.merchant_confirm_sell,name='merchant_confirm_sell'),
    path('p2p/sell-order/<int:order_id>/seller-release/', views.seller_confirm_release, name='seller_release'),
]
