from django import forms

class DepositForm(forms.Form):
    currency = forms.ChoiceField(choices=[('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP')])
    amount = forms.DecimalField(max_digits=10, decimal_places=2, min_value=1)