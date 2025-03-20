from django.contrib import admin
from .models import Crypto, CryptoPurchase

@admin.register(Crypto)
class CryptoAdmin(admin.ModelAdmin):
    list_display = ("name", "symbol", "price_rate", "available")  # Display columns
    search_fields = ("name", "symbol")  # Enable search by name or symbol
    list_filter = ("available",)  # Filter by availability
    ordering = ("name",)

@admin.register(CryptoPurchase)
class CryptoPurchaseAdmin(admin.ModelAdmin):
    list_display = ("user", "crypto", "amount", "wallet_address", "timestamp", "status")
    search_fields = ("user__username", "crypto__name", "crypto__symbol")
    list_filter = ("status",)
    ordering = ("-timestamp",)
