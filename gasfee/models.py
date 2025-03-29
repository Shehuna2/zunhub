from django.db import models
from django.conf import settings
from django.contrib.auth.models import User


class Crypto(models.Model):
    NETWORK_CHOICES = [
        ('ETH', 'Ethereum'),
        ('BNB', 'Binance Smart Chain'),
        ('ARB', 'Arbitrum'),
        ('BASE', 'Base'),
        ('OP', 'Optimism'),
    ]
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=10, unique=True)
    logo = models.ImageField(upload_to='images/', default='default_logo.png')
    coingecko_id = models.CharField(max_length=50, null=True)
    network = models.CharField(max_length=50, choices=NETWORK_CHOICES) 

    class Meta:
        unique_together = ('coingecko_id', 'network')  # Ensures ETH on Arbitrum/Base are separate

    def save(self, *args, **kwargs):
        if self.network in ['ARB', 'BASE', 'OP']:  # If it's an L2 ETH token
            self.coingecko_id = 'ethereum'  # Ensure correct ID
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.symbol}) on {self.network}"
    
    
class CryptoPurchase(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    crypto = models.ForeignKey('Crypto', on_delete=models.CASCADE)  # Adjust 'Crypto' to your app’s model name
    input_amount = models.DecimalField(max_digits=20, decimal_places=8)  # Amount user entered
    input_currency = models.CharField(max_length=10)  # NGN, USDT, or crypto symbol
    crypto_amount = models.DecimalField(max_digits=20, decimal_places=8)  # Actual crypto received
    total_price = models.DecimalField(max_digits=20, decimal_places=2)  # Total cost in NGN
    wallet_address = models.CharField(max_length=255)
    status = models.CharField(max_length=20, default="pending")
    tx_hash = models.CharField(max_length=255, blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True) 


    def __str__(self):
        return f"{self.user.username} - {self.crypto.symbol} - ₦{self.crypto_amount} - ₦{self.total_price} ({self.status})"


class ExchangeRateMargin(models.Model):
    currency_pair = models.CharField(max_length=20, default="USDT/NGN", unique=True)
    profit_margin = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # NGN amount to add
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.currency_pair} Margin: ₦{self.profit_margin}"