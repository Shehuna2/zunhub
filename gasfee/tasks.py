import time
import logging
from celery import shared_task
from django.core.mail import send_mail
from django.utils.timezone import now
from .models import CryptoPurchase
from .utils import get_transaction_hash

logger = logging.getLogger(__name__)


@shared_task
def process_crypto_order(order_id):
    """Automates order processing"""
    try:
        order = CryptoPurchase.objects.get(id=order_id)

        if order.status == "pending":
            # Simulate payment verification & crypto transfer
            order.status = "completed"
            order.processed_at = now()
            order.save()

            # Notify user via email (optional)
            send_mail(
                "Your Crypto Purchase is Complete",
                f"Your order for {order.input_amount} {order.crypto.symbol} has been completed.",
                "admin@zunhub.com",
                [order.user.email],
                fail_silently=True,
            )

        return f"Order {order_id} processed successfully."
    except CryptoPurchase.DoesNotExist:
        return f"Order {order_id} not found."




@shared_task
def update_ton_tx_hash(order_id, sender_address, receiver_address, amount_ton):
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            tx_hash = get_transaction_hash(sender_address, receiver_address, amount_ton)
            if tx_hash != "pending":
                order = CryptoPurchase.objects.get(id=order_id)
                order.tx_hash = tx_hash
                order.save(update_fields=["tx_hash"])
                logger.info(f"Updated tx_hash for order {order_id}: {tx_hash}")
                return
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}: Failed to retrieve hash: {e}")
        time.sleep(30)
    logger.warning(f"Could not retrieve hash for order {order_id} after {max_attempts} attempts")