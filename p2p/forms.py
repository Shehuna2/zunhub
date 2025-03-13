from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, SellOffer, Order

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class SellOfferForm(forms.ModelForm):
    class Meta:
        model = SellOffer
        fields = ['amount_available', 'min_amount', 'max_amount', 'price_per_unit']

    def clean_max_amount(self):
        max_amount = self.cleaned_data['max_amount']
        amount_available = self.cleaned_data['amount_available']
        if max_amount > amount_available:
            raise forms.ValidationError("Max amount cannot exceed available balance.")
        return max_amount

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['amount_requested']

    def __init__(self, *args, **kwargs):
        self.sell_offer = kwargs.pop('sell_offer', None)
        super().__init__(*args, **kwargs)

    def clean_amount_requested(self):
        amount = self.cleaned_data['amount_requested']
        if amount < self.sell_offer.min_amount or amount > self.sell_offer.max_amount:
            raise forms.ValidationError(f"Amount must be between {self.sell_offer.min_amount} and {self.sell_offer.max_amount}.")
        return amount
