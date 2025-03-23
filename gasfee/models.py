from django.db import models
from django.conf import settings
from django.contrib.auth.models import User


class Crypto(models.Model):
    name = models.CharField(max_length=50, unique=True)
    symbol = models.CharField(max_length=10, unique=True)
    logo = models.ImageField(upload_to='images/', default='default_logo.png')
    coingecko_id = models.CharField(max_length=50, unique=True, null=True)  # Added for API consistency

    def __str__(self):
        return f"{self.name} ({self.symbol} {self.coingecko_id})"
    
class CryptoPurchase(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    crypto = models.ForeignKey('Crypto', on_delete=models.CASCADE)  # Adjust 'Crypto' to your app’s model name
    input_amount = models.DecimalField(max_digits=20, decimal_places=8)  # Amount user entered
    input_currency = models.CharField(max_length=10)  # NGN, USDT, or crypto symbol
    crypto_amount = models.DecimalField(max_digits=20, decimal_places=8)  # Actual crypto received
    total_price = models.DecimalField(max_digits=20, decimal_places=2)  # Total cost in NGN
    wallet_address = models.CharField(max_length=255)
    status = models.CharField(max_length=20, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)  # Optional


    def __str__(self):
        return f"{self.user.username} - {self.crypto.symbol} - ₦{self.crypto_amount} - ₦{self.total_price} ({self.status})"


class ExchangeRateMargin(models.Model):
    currency_pair = models.CharField(max_length=20, default="USDT/NGN", unique=True)
    profit_margin = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # NGN amount to add
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.currency_pair} Margin: ₦{self.profit_margin}"