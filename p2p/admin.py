from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Wallet, SellOffer, Order, UserProfile

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_merchant', 'is_staff', 'is_superuser')
    list_filter = ('is_merchant', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email')
    fieldsets = UserAdmin.fieldsets + (
        ('Merchant Info', {'fields': ('is_merchant',)}),
    )
    actions = ['make_merchant', 'remove_merchant']

    def make_merchant(self, request, queryset):
        queryset.update(is_merchant=True)
    make_merchant.short_description = "Grant Merchant Role"

    def remove_merchant(self, request, queryset):
        queryset.update(is_merchant=False)
    remove_merchant.short_description = "Remove Merchant Role"


class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance")
    actions = ["add_funds"]

    def add_funds(self, request, queryset):
        for wallet in queryset:
            wallet.deposit(5000)  # Add NGN 5000 for testing
        self.message_user(request, "Added NGN 5000 to selected wallets.")

    add_funds.short_description = "Add NGN 5000 to selected wallets"


admin.site.register(User, CustomUserAdmin)
admin.site.register(Wallet, WalletAdmin)
admin.site.register(SellOffer)
admin.site.register(Order)
admin.site.register(UserProfile)