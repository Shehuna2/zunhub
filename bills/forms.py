from django import forms
from decimal import Decimal
from .models import ASSET_CHOICES, EXCHANGE_CHOICES

class SellStep1Form(forms.Form):
    asset = forms.ChoiceField(choices=ASSET_CHOICES, label="Asset")
    source = forms.ChoiceField(choices=EXCHANGE_CHOICES, label="Send From")
    amount_asset = forms.DecimalField(min_value=Decimal('0.0001'), decimal_places=8, label="Amount to Sell")
