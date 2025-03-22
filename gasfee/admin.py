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
    list_display = ("user", "crypto", "input_amount", "input_currency", "crypto_amount", "total_price", "status", "created_at")
    list_filter = ("status", "input_currency", "crypto", "created_at")
    search_fields = ("user__username", "crypto__symbol", "wallet_address")
    readonly_fields = ("created_at",)
    fieldsets = (
        (None, {
            "fields": ("user", "crypto", "wallet_address", "status")
        }),
        ("Purchase Details", {
            "fields": ("input_amount", "input_currency", "crypto_amount", "total_price")
        }),
        ("Metadata", {
            "fields": ("created_at",)
        }),
    )
