from django.conf import settings
from django.db import models
from decimal import Decimal

EXCHANGE_CHOICES = [
    ('binance', 'Binance'),
    ('bybit',   'Bybit'),
    ('mexc',    'MEXC'),
    ('gateio',  'Gate.io'),
    ('bitget',  'Bitget'),
    ('wallet',  'External Wallet'),
]

ASSET_CHOICES = [
    ('usdt', 'USDT'),
    ('bnb',  'BNB'),
]


class ExchangeInfo(models.Model):
    exchange = models.CharField(max_length=20, choices=EXCHANGE_CHOICES, unique=True)
    receive_qr = models.ImageField(upload_to='exchange_qrcodes/', blank=True, null=True,)
    contact_info = models.JSONField(blank=True, null=True, default=dict)
    
    def __str__(self):
        return self.get_exchange_display()


class AssetSellOrder(models.Model):
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    asset        = models.CharField(max_length=10, choices=ASSET_CHOICES)
    source       = models.CharField(max_length=20, choices=EXCHANGE_CHOICES)
    amount_asset = models.DecimalField(max_digits=18, decimal_places=8)
    rate_ngn     = models.DecimalField(max_digits=20, decimal_places=4)   # snapshot of rate
    amount_ngn   = models.DecimalField(max_digits=20, decimal_places=2)   # computed total
    status       = models.CharField(max_length=20, default='pending')
    details      = models.JSONField(blank=True, default=dict)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} → Platform: {self.amount_asset} {self.asset.upper()} for ₦{self.amount_ngn}"

class PaymentProof(models.Model):
    order = models.OneToOneField(AssetSellOrder, on_delete=models.CASCADE, related_name="proof")
    image = models.ImageField(upload_to="payment_proofs/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Proof for Order #{self.order.id}"