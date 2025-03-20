from django.db import models
from django.conf import settings
from django.contrib.auth.models import User


class Crypto(models.Model):
    name = models.CharField(max_length=50, unique=True)
    symbol = models.CharField(max_length=10, unique=True)
    price_rate = models.DecimalField(default=0.00, max_digits=15, decimal_places=2)  # Admin sets NGN rate
    available = models.BooleanField(default=True)  # Admin controls availability

    def __str__(self):
        return f"{self.name} ({self.symbol})"
    
class CryptoPurchase(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    crypto = models.ForeignKey(Crypto, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=15, decimal_places=8)  # Crypto amount
    total_price = models.DecimalField(max_digits=15, decimal_places=2)  # NGN price
    wallet_address = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    def __str__(self):
        return f"{self.user.username} - {self.crypto.symbol} - ₦{self.amount} - ₦{self.total_price} ({self.status})"


