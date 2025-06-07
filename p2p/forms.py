from django import forms
from django.db.models import Sum
from django.core.exceptions import ValidationError

from .models import Withdraw_P2P_Offer, DepositOrder, Dispute, Wallet, Deposit_P2P_Offer, WithdrawOrder



class WithdrawOfferForm(forms.ModelForm):
    class Meta:
        model = Withdraw_P2P_Offer
        fields = ['amount_available', 'min_amount', 'max_amount', 'price_per_unit']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

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
    
    
class WithdrawOrderForm(forms.ModelForm):
    class Meta:
        model = WithdrawOrder
        fields = ['amount_requested']

    def __init__(self, *args, buy_offer=None, user=None, **kwargs):
        """
        buy_offer: the Withdraw_P2P_Offer instance
        user: the User who’s selling (i.e. request.user)
        """
        self.buy_offer = buy_offer
        self.user      = user
        super().__init__(*args, **kwargs)

        if buy_offer:
            w = self.fields['amount_requested'].widget
            w.attrs.update({
                'min': buy_offer.min_amount,
                'max': buy_offer.max_amount,
                'step': '0.01',
            })

    def clean_amount_requested(self):
        amt = self.cleaned_data['amount_requested']

        # 1) Offer-level checks
        if amt < self.buy_offer.min_amount or amt > self.buy_offer.max_amount:
            raise ValidationError(
                f"Must sell between ₦{self.buy_offer.min_amount} and ₦{self.buy_offer.max_amount}."
            )
        if amt > self.buy_offer.amount_available:
            raise ValidationError("Merchant doesn’t have that many units left.")

        # 2) Seller-wallet check
        wallet = Wallet.objects.get(user=self.user)
        available = wallet.balance - wallet.locked_balance
        if amt > available:
            raise ValidationError(
                f"You only have ₦{available} available to lock in your wallet."
            )

        return amt
    

class DepositOfferForm(forms.ModelForm):
    class Meta:
        model = Deposit_P2P_Offer
        fields = ['amount_available', 'max_amount', 'min_amount', 'price_per_unit']

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_amount_available(self):
        amount_available = self.cleaned_data['amount_available']
        wallet = Wallet.objects.get(user=self.user)
        available = wallet.balance - wallet.locked_balance
        # Sum of amount_available from other active sell offers
        other_offers = Deposit_P2P_Offer.objects.filter(merchant=self.user, is_available=True).exclude(id=self.instance.id if self.instance else None)
        total_committed = other_offers.aggregate(Sum('amount_available'))['amount_available__sum'] or 0
        if total_committed + amount_available > available:
            raise forms.ValidationError(f"Total amount available across all offers cannot exceed your available balance of ₦{available}.")
        return amount_available


class DepositOrderForm(forms.ModelForm):
    class Meta:
        model = DepositOrder
        fields = ['amount_requested']

    def __init__(self, *args, sell_offer=None, user=None, **kwargs):
        """
        sell_offer: the Deposit_P2P_Offer instance
        user: the User who’s buying (i.e. request.user)
        """
        self.sell_offer = sell_offer
        self.user       = user
        super().__init__(*args, **kwargs)

        if sell_offer:
            w = self.fields['amount_requested'].widget
            w.attrs.update({
                'min': sell_offer.min_amount,
                'max': sell_offer.max_amount,
                'step': '0.01',
            })

    def clean_amount_requested(self):
        amt = self.cleaned_data['amount_requested']

        # 1) Offer-level checks
        if amt < self.sell_offer.min_amount or amt > self.sell_offer.max_amount:
            raise ValidationError(
                f"Must buy between ₦{self.sell_offer.min_amount} and ₦{self.sell_offer.max_amount}."
            )
        if amt > self.sell_offer.amount_available:
            raise ValidationError("Not enough units available from this merchant.")

        # 2) Merchant-wallet check
        from .models import Wallet
        wallet = Wallet.objects.get(user=self.sell_offer.merchant)
        merchant_available = wallet.balance - wallet.locked_balance
        if amt > merchant_available:
            raise ValidationError(
                f"Merchant only has ₦{merchant_available} available to back this offer."
            )

        return amt









# class WithdrawOrderForm(forms.ModelForm):
#     class Meta:
#         model = WithdrawOrder
#         fields = ['amount_requested']

#     def __init__(self, *args, **kwargs):
#         self.buy_offer = kwargs.pop('buy_offer')
#         super().__init__(*args, **kwargs)

#     def clean_amount_requested(self):
#         amt = self.cleaned_data['amount_requested']
#         # check against offer
#         if amt < self.buy_offer.min_amount or amt > self.buy_offer.max_amount:
#             raise forms.ValidationError("Outside merchant’s allowed range.")
#         # check user funds
#         wallet = Wallet.objects.get(user=self.initial['seller'])
#         if amt > wallet.balance - wallet.locked_balance:
#             raise forms.ValidationError("Insufficient tokens to sell.")
#         return amt

# class DepositOrderForm(forms.ModelForm):
#     class Meta:
#         model = DepositOrder
#         fields = ['amount_requested']

#     def __init__(self, *args, **kwargs):
#         # pop off the SellOffer, then fetch the merchant’s wallet
#         self.sell_offer = kwargs.pop('sell_offer', None)
#         super().__init__(*args, **kwargs)
#         if self.sell_offer:
#             from .models import Wallet
#             self.merchant_wallet = Wallet.objects.get(user=self.sell_offer.merchant)
#         else:
#             self.merchant_wallet = None

#     def clean_amount_requested(self):
#         amount = self.cleaned_data.get('amount_requested')

#         # 1. Check against offer’s min/max
#         if amount < self.sell_offer.min_amount or amount > self.sell_offer.max_amount:
#             raise forms.ValidationError(
#                 f"Amount must be between {self.sell_offer.min_amount} and {self.sell_offer.max_amount}."
#             )

#         # 2. Check merchant’s available balance
#         if self.merchant_wallet:
#             available = self.merchant_wallet.balance - self.merchant_wallet.locked_balance
#             if amount > available:
#                 raise forms.ValidationError(
#                     f"Merchant only has ₦{available} available to lock."
#                 )

#         return amount
    

class DisputeForm(forms.ModelForm):
    class Meta:
        model = Dispute
        fields = ["reason", "proof"]  # Only allow reason and proof upload
