import requests
from django.core.cache import cache
from django.core.mail import send_mail



def get_usdt_ngn_rate():
    """Fetch and cache USDT to NGN rate with ₦100 profit."""
    cache_key = "usdt_ngn_rate"
    cached_rate = cache.get(cache_key)

    if cached_rate:
        return cached_rate  # Return cached rate if available

    # Fetch real-time rate from Binance API
    url = "https://api.binance.com/api/v3/ticker/price?symbol=USDTNGN"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        usdt_rate = float(data["price"]) + 100  # Add ₦100 profit
    except (requests.RequestException, ValueError):
        usdt_rate = 1600  # Default fallback rate

    cache.set(cache_key, usdt_rate, timeout=600)  # Cache for 10 mins
    return usdt_rate

def send_order_email(user_email, order):
    subject = f"Your {order.crypto} Purchase is Completed"
    message = f"Your order for {order.amount} {order.crypto} has been processed. \nTransaction Hash: {order.transaction_hash}"
    send_mail(subject, message, "no-reply@yourapp.com", [user_email])