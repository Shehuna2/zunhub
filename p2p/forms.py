from django import forms
from .models import SellOffer, Order, Dispute, Wallet, BuyOffer, SellOrder



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
    

class BuyOfferForm(forms.ModelForm):
    class Meta:
        model = BuyOffer
        fields = ['amount_available', 'min_amount', 'max_amount', 'price_per_unit']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

    def clean_amount_available(self):
        amt = self.cleaned_data['amount_available']
        wallet = Wallet.objects.get(user=self.user)
        if amt > wallet.balance - wallet.locked_balance:
            raise forms.ValidationError("Not enough tokens to back this offer.")
        return amt

    def clean_max_amount(self):
        max_amt = self.cleaned_data['max_amount']
        amt = self.cleaned_data.get('amount_available')
        if amt and max_amt > amt:
            raise forms.ValidationError("Max amount cannot exceed amount available.")
        return max_amt
    def clean(self):
        cleaned_data = super().clean()
        min_amt = cleaned_data.get('min_amount')
        max_amt = cleaned_data.get('max_amount')
        if min_amt and max_amt and min_amt > max_amt:
            raise forms.ValidationError("Min amount cannot be greater than max amount.")
        return cleaned_data
    
class SellOrderForm(forms.ModelForm):
    class Meta:
        model = SellOrder
        fields = ['amount_requested']

    def __init__(self, *args, **kwargs):
        self.buy_offer = kwargs.pop('buy_offer')
        super().__init__(*args, **kwargs)

    def clean_amount_requested(self):
        amt = self.cleaned_data['amount_requested']
        # check against offer
        if amt < self.buy_offer.min_amount or amt > self.buy_offer.max_amount:
            raise forms.ValidationError("Outside merchant’s allowed range.")
        # check user funds
        wallet = Wallet.objects.get(user=self.initial['seller'])
        if amt > wallet.balance - wallet.locked_balance:
            raise forms.ValidationError("Insufficient tokens to sell.")
        return amt

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
