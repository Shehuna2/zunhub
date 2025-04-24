from django.db import models
from decimal import Decimal
from django.conf import settings

class CurrencyRate(models.Model):
    currency = models.CharField(max_length=3, unique=True)  # e.g., USD, EUR, GBP
    base_rate = models.DecimalField(max_digits=10, decimal_places=4)  # Rate to NGN
    markup = models.DecimalField(max_digits=5, decimal_places=4, default=0.02)  # 2% markup
    last_updated = models.DateTimeField(auto_now=True)

    def effective_rate(self):
        if self.base_rate is None or self.markup is None:
            return None
        return self.base_rate * (Decimal('1') + self.markup)



class DepositRequest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    currency = models.CharField(max_length=3)  # e.g., USD, EUR, GBP
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Amount in original currency
    ngn_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Converted NGN amount
    tx_ref = models.CharField(max_length=100, unique=True)  # Unique transaction reference
    status = models.CharField(max_length=20, default='pending')  # pending, successful, failed
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} {self.currency} ({self.status})"

