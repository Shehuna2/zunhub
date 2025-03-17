from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Wallet, SellOffer, Order, UserProfile, Dispute
from .views import admin_dashboard
from .utils import notify_users
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

@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ("order", "buyer", "status", "created_at", "resolved_at")
    list_filter = ("status",)
    search_fields = ("order__id", "buyer__username")
    actions = ["resolve_buyer_favor", "resolve_merchant_favor"]

    def resolve_buyer_favor(self, request, queryset):
        for dispute in queryset:
            dispute.status = 'resolved_buyer'
            dispute.order.status = 'completed'  # Update order status
            dispute.order.buyer.wallet.balance += dispute.order.total_price  # Release funds
            dispute.order.save()
            dispute.save()

            # Notify buyer & merchant
            notify_users(
                "Dispute Resolved in Buyer's Favor",
                f"Your dispute for Order #{dispute.order.id} has been resolved in your favor. Funds have been released.",
                [dispute.buyer.email]
            )
            notify_users(
                "Dispute Resolved - Funds Released",
                f"The dispute for Order #{dispute.order.id} was resolved in the buyer’s favor. Funds have been released.",
                [dispute.order.sell_offer.merchant.email]
            )
        self.message_user(request, "Dispute resolved in buyer's favor and funds released.")

    resolve_buyer_favor.short_description = "Resolve in Buyer's Favor (release funds to buyer)"


    def resolve_merchant_favor(self, request, queryset):
        for dispute in queryset:
            dispute.status = 'resolved_merchant'
            dispute.order.status = 'cancelled'  # Update order status
            dispute.order.sell_offer.merchant.wallet.balance += dispute.order.total_price  # Refund merchant
            dispute.order.save()
            dispute.save()

            # Notify buyer & merchant
            notify_users(
                "Dispute Resolved in Buyer's Favor",
                f"Your dispute for Order #{dispute.order.id} has been resolved in your favor. Funds have been released.",
                [dispute.buyer.email]
            )
            notify_users(
                "Dispute Resolved - Funds Released",
                f"The dispute for Order #{dispute.order.id} was resolved in the buyer’s favor. Funds have been released.",
                [dispute.order.sell_offer.merchant.email]
            )
        self.message_user(request, "Dispute resolved in merchant's favor and funds refunded.")

    resolve_merchant_favor.short_description = "Resolve in Merchant's Favor (refund merchant)"

    def reject_dispute(self, request, queryset):
        for dispute in queryset:
            dispute.status = 'rejected'
            dispute.save()
        self.message_user(request, "Dispute rejected, no funds released.")

    reject_dispute.short_description = "Reject Dispute (Keep funds in escrow)"



admin.site.register(User, CustomUserAdmin)
admin.site.register(Wallet, WalletAdmin)
admin.site.register(SellOffer)
admin.site.register(Order)
admin.site.register(UserProfile)