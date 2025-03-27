import os
import requests
import logging
import traceback
from decimal import Decimal

from django.core.cache import cache
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from django.contrib import messages
from web3 import Web3

from p2p.models import Wallet
from .models import CryptoPurchase, Crypto
from .utils import get_crypto_price, get_exchange_rate, send_bsc, send_ton, is_valid_ton_wallet
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
logger = logging.getLogger(__name__)

@login_required
def buy_crypto(request, crypto_id):
    crypto = get_object_or_404(Crypto, id=crypto_id)

    # Fetch cached values
    crypto_price = cache.get(f"crypto_price_{crypto.coingecko_id}")
    exchange_rate = cache.get("exchange_rate_usd_ngn")

    if crypto_price is None:
        crypto_price = get_crypto_price(crypto.coingecko_id)
        cache.set(f"crypto_price_{crypto.coingecko_id}", crypto_price, timeout=300)

    if exchange_rate is None:
        exchange_rate = get_exchange_rate()
        cache.set("exchange_rate_usd_ngn", exchange_rate, timeout=300)

    if request.method == "POST":
        wallet_address = request.POST.get("wallet_address")

        # Validate wallet address
        if crypto.symbol.upper() == "TON" and not is_valid_ton_wallet(wallet_address):
            return JsonResponse({"success": False, "error": "Invalid TON wallet address."})

        try:
            amount = Decimal(request.POST.get("amount", "0"))
            if amount <= 0:
                raise ValueError("Invalid amount")

            currency = request.POST.get("currency", "NGN").upper()
            logger.info(f"Processing purchase: {amount} {currency} to {wallet_address}")

            # Convert to crypto received
            if currency == "NGN":
                total_price_ngn = amount
                crypto_received = (amount / exchange_rate) / crypto_price
            elif currency == "USDT":
                crypto_received = amount / crypto_price
                total_price_ngn = amount * exchange_rate
            elif currency == crypto.symbol.upper():
                crypto_received = amount
                total_price_ngn = (amount * crypto_price) * exchange_rate
            else:
                return JsonResponse({"success": False, "error": "Invalid currency selection."})

            # Deduct NGN balance
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=request.user)
                if wallet.balance < total_price_ngn:
                    return JsonResponse({"success": False, "error": "Insufficient NGN balance."})

                wallet.balance -= total_price_ngn
                wallet.save(update_fields=["balance"])

                order = CryptoPurchase.objects.create(
                    user=request.user,
                    crypto=crypto,
                    input_amount=amount,
                    input_currency=currency,
                    crypto_amount=crypto_received,
                    total_price=total_price_ngn,
                    wallet_address=wallet_address,
                    status="pending"
                )

            # Send crypto to user's wallet
            try:
                tx_hash = send_ton(wallet_address, crypto_received) if crypto.symbol.upper() == "TON" else send_bsc(wallet_address, crypto_received)

                order.tx_hash = tx_hash
                order.status = "completed"
                order.save(update_fields=["tx_hash", "status"])

                return JsonResponse({
                    "success": True,
                    "message": f"Your {crypto_received:.6f} {crypto.symbol} has been sent!",
                    "tx_hash": tx_hash
                })
            except Exception as tx_error:
                logger.error(f"Crypto transfer failed: {tx_error}\n{traceback.format_exc()}")

                # Refund on failure
                refund_user(request, order)

                return JsonResponse({"success": False, "error": "Transaction failed. Refund issued."})

        except (ValueError, TypeError) as e:
            return JsonResponse({"success": False, "error": "Invalid amount input."})

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({
            "crypto_price": float(crypto_price),
            "exchange_rate": float(exchange_rate),
        })

    return render(request, "gasfee/buy_crypto.html", {
        "crypto": crypto,
        "exchange_rate": exchange_rate,
        "crypto_price": crypto_price,
    })

def asset_list(request):
    """Returns a list of available crypto assets."""
    cryptos = Crypto.objects.all()
    return render(request, "gasfee/crypto_list.html", {"cryptos": cryptos})

def refund_user(request, purchase):
    """Refunds a user if an order fails."""
    if purchase.status == "failed":  # Prevent double refunds
        return False

    try:
        wallet = Wallet.objects.get(user=purchase.user)
        wallet.balance += purchase.total_price
        wallet.save()

        purchase.status = "failed"
        purchase.save()

        messages.error(request, f"Your order for {purchase.input_amount} {purchase.crypto.symbol} failed. Refund issued.")
        return True
    except Wallet.DoesNotExist:
        messages.error(request, "Wallet not found. Refund could not be processed.")
        return False

def update_order_status(request, order_id, new_status):
    """Updates order status and refunds if necessary."""
    purchase = get_object_or_404(CryptoPurchase, id=order_id)

    if new_status == "failed":
        refund_user(request, purchase)

    purchase.status = new_status
    purchase.save()
