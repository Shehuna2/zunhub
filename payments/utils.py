import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Flutterwave API endpoint for initiating payments
FLW_API_URL = "https://api.flutterwave.com/v3/payments"

def initiate_flutterwave_payment(
    tx_ref,
    amount,
    currency,
    redirect_url,
    customer_email,
    customer_name,
    customer_phone=None
):
    """
    Initiate a payment with Flutterwave v3.

    Args:
        tx_ref (str): Unique transaction reference.
        amount (Decimal|float|int): Amount to charge.
        currency (str): Currency code (e.g., 'USD').
        redirect_url (str): URL to redirect after payment.
        customer_email (str): Customer's email address.
        customer_name (str): Customer's name.
        customer_phone (str, optional): Customer's phone number.

    Returns:
        str|None: Payment link on success, None otherwise.
    """
    # Ensure the secret key is present and clean
    secret_key = getattr(settings, 'FLUTTERWAVE_SECRET_KEY', '').strip()
    if not secret_key:
        logger.error("Flutterwave secret key not configured.")
        return None

    headers = {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "tx_ref": tx_ref,
        "amount": float(amount),  # Convert Decimal to float if needed
        "currency": currency,
        "redirect_url": redirect_url,
        "customer": {
            "email": customer_email,
            "name": customer_name,
        },
        "customizations": {
            "title": "Deposit to Wallet",
            "description": f"Deposit {amount} {currency} to your wallet",
        }
    }

    # Optionally include the phone number
    if customer_phone:
        payload["customer"]["phonenumber"] = customer_phone

    logger.info(
        "Initiating FLW payment: url=%s, payload=%s",
        FLW_API_URL,
        payload
    )

    try:
        # Add a timeout to avoid hanging
        response = requests.post(
            FLW_API_URL,
            json=payload,
            headers=headers,
            timeout=10
        )
        logger.info(
            "Flutterwave response: status=%s, headers=%s, body=%s",
            response.status_code,
            response.headers,
            response.text
        )

        if response.status_code == 200:
            link = response.json().get('data', {}).get('link')
            if link:
                return link
            logger.error("No payment link returned by Flutterwave.")
        else:
            logger.error(
                "Flutterwave error: %s %s",
                response.status_code,
                response.text
            )
            if response.status_code == 403:
                logger.error(
                    "403 Forbidden: Check secret key, endpoint, IP whitelisting, and account status in dashboard."
                )
    except requests.RequestException as e:
        logger.exception("Error initiating Flutterwave payment: %s", e)

    return None


