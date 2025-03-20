import requests
from django.core.cache import cache
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from decimal import Decimal
from django.contrib import messages

from p2p.models import Wallet
from .models import CryptoPurchase, Crypto

def asset_list(request):
    cryptos = Crypto.objects.all()

    return render(request, "gasfee/crypto_list.html", {"cryptos": cryptos})



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
        usdt_rate = 1500  # Default fallback rate

    cache.set(cache_key, usdt_rate, timeout=600)  # Cache for 10 mins
    return usdt_rate


@login_required
def buy_crypto(request, crypto_id):
    crypto = get_object_or_404(Crypto, id=crypto_id) 
    exchange_rate = get_usdt_ngn_rate()

    if request.method == "POST":
        wallet_address = request.POST.get("wallet_address")
        amount = float(request.POST.get("amount", 0))
        currency = request.POST.get("currency", "ngn").upper()

        if amount <= 0:
            messages.error(request, "Invalid amount.")
            return redirect("buy_crypto", crypto_id=crypto.id)

        if currency == "NGN":
            total_price = amount  
        elif currency == "USDT":
            total_price = amount * exchange_rate  
        elif currency == crypto.symbol.upper():
            total_price = amount * float(crypto.price_rate)  
        else:
            messages.error(request, "Invalid currency selection.")
            return redirect("buy_crypto", crypto_id=crypto.id)

        wallet = Wallet.objects.get(user=request.user)

        if wallet.balance < total_price:
            messages.error(request, "Insufficient balance.")
            return redirect("buy_crypto", crypto_id=crypto.id)

        wallet.balance -= Decimal(total_price)
        wallet.save()

        CryptoPurchase.objects.create(
            user=request.user,
            crypto=crypto,
            amount=amount,
            total_price=total_price,
            wallet_address=wallet_address,
            status="pending"
        )

        # Store success message in session storage (accessed via JS)
        request.session["success_message"] = f"You have successfully purchased {amount} {crypto.symbol}."

        return JsonResponse({"success": True})  # Send JSON response to trigger modal

    return render(request, "gasfee/buy_crypto.html", {
        "crypto": crypto,
        "exchange_rate": exchange_rate,
    })



def refund_user(request, purchase):
    """Refunds a user if an order fails."""
    try:
        wallet = Wallet.objects.get(user=purchase.user)
        wallet.balance += purchase.total_price  # Refund the total amount
        wallet.save()

        # Update purchase status
        purchase.status = "failed"
        purchase.save()

        # Notify user
        messages.error(request, f"Your order for {purchase.amount} {purchase.crypto.symbol} failed. Refund issued.")
        return True
    except Wallet.DoesNotExist:
        messages.error(request, "Wallet not found. Refund could not be processed.")
        return False

def update_order_status(request, order_id, new_status):
    """Updates the status of an order and refunds if necessary."""
    purchase = get_object_or_404(CryptoPurchase, id=order_id)

    if new_status == "failed" and purchase.status != "failed":
        refund_user(request, purchase)

    purchase.status = new_status
    purchase.save()
