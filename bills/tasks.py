# p2p/tasks.py

from celery import shared_task
from django.utils import timezone
from decimal import Decimal

from .models import AssetSellOrder
from .services import verify_transfer
from p2p.models import Wallet

@shared_task
def check_sell_orders():
    """
    Periodic task: find all SellOrders awaiting_confirmation,
    verify if payment has arrived, and credit user's NGN wallet.
    """
    pending = AssetSellOrder.objects.filter(status='awaiting_confirmation')
    for order in pending:
        # Attempt to verify the transfer
        success = verify_transfer(order)
        if success:
            # Mark order completed
            order.status = 'completed'
            order.save()

            # Credit the user's wallet
            wallet, _ = Wallet.objects.get_or_create(user=order.user)
            wallet.deposit(order.amount_ngn)

            # (Optional) send notification to user, e.g. email or in-app
