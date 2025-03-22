from django.core.management.base import BaseCommand
from django.utils import timezone
from gasfee.models import CryptoPurchase
from gasfee.views import send_crypto

class Command(BaseCommand):
    help = "Process pending crypto purchase orders"

    def handle(self, *args, **kwargs):
        pending_orders = CryptoPurchase.objects.filter(status="pending")
        for order in pending_orders:
            print(f"Processing order {order.id} for {order.crypto}")
            success = send_crypto(order)
            if success:
                print(f"Order {order.id} completed.")
            else:
                print(f"Order {order.id} failed.")
