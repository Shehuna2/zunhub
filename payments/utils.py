import requests
from django.conf import settings

def initiate_flutterwave_payment(tx_ref, amount, currency, redirect_url, customer_email, customer_name):
    url = "https://api.flutterwave.com/v3/payments"
    headers = {
        "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "tx_ref": tx_ref,
        "amount": str(amount),
        "currency": currency,
        "redirect_url": redirect_url,
        "customer": {
            "email": customer_email,
            "name": customer_name,
        },
        "customizations": {
            "title": "Deposit to Wallet",
            "description": f"Deposit {amount} {currency} to your NGN wallet",
        }
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        return response.json()['data']['link']
    return None