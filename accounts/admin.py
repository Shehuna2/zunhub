from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
from p2p.models import Wallet
from django.urls import reverse, path
from django.utils.html import format_html


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


class CustomAdminSite(admin.AdminSite):
    site_header = "Admin Panel"

    def admin_dashboard_link(self):
        url = reverse("admin_dashboard")
        return format_html('<a href="{}" class="button">Order Metrics Dashboard</a>', url)

admin_site = CustomAdminSite(name="custom_admin")


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