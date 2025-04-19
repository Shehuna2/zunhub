from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, SellOffer, Order, Dispute, Wallet

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class SellOfferForm(forms.ModelForm):
    class Meta:
        model = SellOffer
        fields = ['amount_available', 'min_amount', 'max_amount', 'price_per_unit']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_amount_available(self):
        amount_available = self.cleaned_data['amount_available']
        if self.user:
            wallet = Wallet.objects.get(user=self.user)
            available = wallet.balance - wallet.locked_balance
            if amount_available > available:
                raise forms.ValidationError(
                    f"Amount available cannot exceed your wallet's available balance of {available}."
                )
        return amount_available

    def clean_max_amount(self):
        max_amount = self.cleaned_data['max_amount']
        amount_available = self.cleaned_data.get('amount_available')
        if amount_available and max_amount > amount_available:
            raise forms.ValidationError("Max amount cannot exceed amount available.")
        return max_amount

    def clean(self):
        cleaned_data = super().clean()
        min_amount = cleaned_data.get('min_amount')
        max_amount = cleaned_data.get('max_amount')
        if min_amount and max_amount and min_amount > max_amount:
            raise forms.ValidationError("Min amount cannot be greater than max amount.")
        return cleaned_data

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['amount_requested']

    def __init__(self, *args, **kwargs):
        # pop off the SellOffer, then fetch the merchant’s wallet
        self.sell_offer = kwargs.pop('sell_offer', None)
        super().__init__(*args, **kwargs)
        if self.sell_offer:
            from .models import Wallet
            self.merchant_wallet = Wallet.objects.get(user=self.sell_offer.merchant)
        else:
            self.merchant_wallet = None

    def clean_amount_requested(self):
        amount = self.cleaned_data.get('amount_requested')

        # 1. Check against offer’s min/max
        if amount < self.sell_offer.min_amount or amount > self.sell_offer.max_amount:
            raise forms.ValidationError(
                f"Amount must be between {self.sell_offer.min_amount} and {self.sell_offer.max_amount}."
            )

        # 2. Check merchant’s available balance
        if self.merchant_wallet:
            available = self.merchant_wallet.balance - self.merchant_wallet.locked_balance
            if amount > available:
                raise forms.ValidationError(
                    f"Merchant only has ₦{available} available to lock."
                )

        return amount
    

class DisputeForm(forms.ModelForm):
    class Meta:
        model = Dispute
        fields = ["reason", "proof"]  # Only allow reason and proof upload
