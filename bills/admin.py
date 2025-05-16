from django.contrib import admin
from .models import AssetSellOrder

@admin.register(AssetSellOrder)
class SellOrderAdmin(admin.ModelAdmin):
    list_display   = (
        'id',
        'user',
        'asset',
        'source',
        'amount_asset',
        'rate_ngn',
        'amount_ngn',
        'status',
        'created_at',
    )
    list_filter    = ('asset', 'source', 'status', 'created_at')
    search_fields  = ('user__username', 'id')
    ordering       = ('-created_at',)
    readonly_fields = ('rate_ngn', 'amount_ngn', 'created_at')

    fieldsets = (
        (None, {
            'fields': ('user', 'asset', 'source', 'amount_asset')
        }),
        ('Computed & Status', {
            'fields': ('rate_ngn', 'amount_ngn', 'status', 'details', 'created_at'),
        }),
    )
