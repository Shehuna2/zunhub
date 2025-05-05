from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Wallet, SellOffer, Order, Dispute, BuyOffer, SellOrder
from .views import admin_dashboard
from .utils import notify_users



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


@admin.register(BuyOffer)
class BuyOfferAdmin(admin.ModelAdmin):
    list_display = ("amount_available", "price_per_unit", "min_amount", "max_amount", "created_at")
    list_filter = ("merchant", "price_per_unit")
    search_fields = ("merchant__username", "price_per_unit")

@admin.register(SellOrder)
class SellOrderAdmin(admin.ModelAdmin):
    list_display = ("buyer_offer", "seller", "amount_requested", "total_price", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("buyer_offer__merchant__username", "seller__username")


admin.site.register(SellOffer)
admin.site.register(Order)
