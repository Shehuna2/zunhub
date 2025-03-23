from django.contrib import admin
from .models import Crypto, CryptoPurchase, ExchangeRateMargin

@admin.register(Crypto)
class CryptoAdmin(admin.ModelAdmin):
    list_display = ("name", "symbol", "coingecko_id")  # Display columns
    search_fields = ("name", "symbol", "coingecko_id")  # Enable search by name or symbol
    list_filter = ("symbol",)  # Filter by availability
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

@admin.register(ExchangeRateMargin)
class ExchangeRateMarginAdmin(admin.ModelAdmin):
    list_display = ("currency_pair", "profit_margin", "updated_at")
    list_editable = ("profit_margin",)  # Edit margin directly in list view
    search_fields = ("currency_pair",)
