from django.contrib import admin
from decimal import Decimal
from .models import CurrencyRate, DepositRequest

@admin.register(CurrencyRate)
class CurrencyRateAdmin(admin.ModelAdmin):
    list_display = ('currency', 'base_rate', 'markup', 'get_effective_rate', 'last_updated')

    def get_effective_rate(self, obj):
        if obj.base_rate is not None and obj.markup is not None:
            return round(obj.base_rate * (Decimal('1') + obj.markup), 4)
        return "-"

    get_effective_rate.short_description = 'Effective Rate'


@admin.register(DepositRequest)
class DepositRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'currency', 'amount', 'ngn_amount', 'tx_ref', 'status', 'created_at')
    list_filter = ('status', 'currency')
    search_fields = ('user__username', 'tx_ref')
