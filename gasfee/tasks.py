from celery import shared_task
from django.core.mail import send_mail
from django.utils.timezone import now
from .models import CryptoPurchase

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
                f"Your order for {order.amount} {order.crypto.symbol} has been completed.",
                "admin@zunhub.com",
                [order.user.email],
                fail_silently=True,
            )

        return f"Order {order_id} processed successfully."
    except CryptoPurchase.DoesNotExist:
        return f"Order {order_id} not found."
