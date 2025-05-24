from django.urls import path
from . import views 

urlpatterns = [
    path('assets/', views.asset_list, name='asset_list'),
    path("buy/<int:crypto_id>/", views.buy_crypto, name="buy_crypto"),
    path('crypto/add/', views.add_crypto_asset, name='add_crypto_asset')
]