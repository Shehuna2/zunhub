import os
import requests
import logging
import traceback
import base58
from web3 import Web3
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from django.contrib import messages
from dotenv import load_dotenv
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test


from .forms import CryptoForm
from p2p.models import Wallet
from .models import CryptoPurchase, Crypto

from .utils import (
    get_crypto_price, get_exchange_rate, send_bsc, send_evm
)
from .near_utils import (
    validate_near_account_id, send_near
)
from .ton_utils import (
    send_ton, validate_ton_address
)
from .sol_utils import (
    send_solana, validate_solana_address, check_solana_balance, 
)

# Load environment variables
load_dotenv()
logger = logging.getLogger(__name__)



@user_passes_test(lambda u: u.is_superuser) 
def add_crypto_asset(request):
    if request.method == 'POST':
        form = CryptoForm(request.POST, request.FILES)  # Add request.FILES for logo
        if form.is_valid():
            form.save()
            return redirect('asset_list')
    else:
        form = CryptoForm()
    return render(request, 'gasfee/create_crypto.html', {'form': form})


def asset_list(request):
    """Renders the crypto dashboard with initial prices & logos."""
    cryptos = Crypto.objects.all()
    # Option A: Fetch initial batch prices (optional)
    coingecko_ids = [c.coingecko_id for c in cryptos]
    cache_key = f"crypto_prices_{'_'.join(sorted(coingecko_ids))}"
    prices = cache.get(cache_key)
    if prices is None:
        try:
            resp = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": ",".join(coingecko_ids), "vs_currencies": "usd"},
                timeout=5,
            )
            resp.raise_for_status()
            prices = resp.json()
            cache.set(cache_key, prices, 300)
        except Exception:
            prices = {}

    crypto_list = []
    for c in cryptos:
        price = prices.get(c.coingecko_id, {}).get("usd", 0.0)
        crypto_list.append({
            "id":        c.id,
            "name":      c.name,
            "symbol":    c.symbol,
            "ws_symbol": f"{c.symbol.lower()}usdt",
            "price":     float(price),
            "logo_url":  c.logo.url,
        })

    return render(request, "gasfee/crypto_list.html", {
        "cryptos": crypto_list,
    })


# Address validators per symbol (excluding EVM, handled inline)
VALIDATORS = {
    "SOL": validate_solana_address,
    "TON": validate_ton_address,
    "NEAR": validate_near_account_id,
}

# Sender functions per symbol
SENDERS = {
    "BNB": send_bsc,
    "SOL": send_solana,
    "TON": send_ton,
    "NEAR": send_near,
    "ETH": send_evm,
    "BASE-ETH": send_evm,
}

@login_required
def buy_crypto(request, crypto_id):
    # Fetch crypto and exchange rate
    crypto = get_object_or_404(Crypto, id=crypto_id)
    exchange_rate = cache.get("exchange_rate_usd_ngn")
    if exchange_rate is None:
        exchange_rate = get_exchange_rate()
        cache.set("exchange_rate_usd_ngn", exchange_rate, 300)

    # Fetch an initial crypto price (USD) for template
    network = crypto.network.lower()
    price_cache_key = f"crypto_price_{crypto.coingecko_id}_{network}"
    crypto_price = cache.get(price_cache_key)
    if crypto_price is None:
        try:
            crypto_price = get_crypto_price(crypto.coingecko_id, crypto.network)
            cache.set(price_cache_key, crypto_price, 300)
        except Exception as e:
            logger.error(f"Failed to fetch initial price for {crypto.symbol}: {e}")
            crypto_price = 0

    if request.method == "POST":
        # Parse and validate input amount
        try:
            amount = Decimal(request.POST.get("amount", "0"))
            if amount <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return JsonResponse({"success": False, "error": "Invalid amount input."})

        currency = request.POST.get("currency", "NGN").upper()
        wallet_address = request.POST.get("wallet_address", "").strip()

        # Wallet address validation and normalization for EVM chains
        symbol = crypto.symbol.upper()
        if symbol in ["BNB", "ETH", "BASE-ETH"]:
            try:
                wallet_address = Web3.to_checksum_address(wallet_address)
            except Exception:
                return JsonResponse({"success": False, "error": "Invalid Ethereum-compatible address."})
        else:
            validator = VALIDATORS.get(symbol)
            if validator and not validator(wallet_address):
                return JsonResponse({"success": False, "error": "Invalid wallet address format."})

        # Convert to crypto quantity and NGN total
        if currency == "NGN":
            total_ngn = amount
            crypto_received = Decimal(request.POST.get("crypto_received", "0"))
        elif currency == "USDT":
            total_ngn = amount * Decimal(exchange_rate)
            crypto_received = Decimal(request.POST.get("crypto_received", "0"))
        elif currency == symbol:
            crypto_received = amount
            total_ngn = amount * Decimal(exchange_rate)
        else:
            return JsonResponse({"success": False, "error": "Invalid currency selection."})

        # Deduct balance and create purchase order
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=request.user)
            if wallet.balance < total_ngn:
                return JsonResponse({
                    "success": False,
                    "error": f"Insufficient balance. Required: {total_ngn}, Available: {wallet.balance}"
                })
            wallet.balance -= total_ngn
            wallet.save(update_fields=["balance"])

            order = CryptoPurchase.objects.create(
                user=request.user,
                crypto=crypto,
                input_amount=amount,
                input_currency=currency,
                crypto_amount=crypto_received,
                total_price=total_ngn,
                wallet_address=wallet_address,
                status="pending"
            )

        # Execute blockchain transfer
        sender = SENDERS.get(symbol)
        if not sender:
            return JsonResponse({"success": False, "error": "Unsupported token."})

        try:
            # NEAR transfer only needs address and amount
            if symbol == "NEAR":
                result = sender(wallet_address, float(crypto_received))
            else:
                result = sender(wallet_address, float(crypto_received), order.id)
            tx_hash = result if isinstance(result, str) else result[0]
        except Exception as e:
            logger.error(f"Transfer failed: {e}", exc_info=True)
            refund_user(request, order)
            return JsonResponse({"success": False, "error": "Transaction failed. Refund issued."})

        # Finalize order
        order.tx_hash = tx_hash
        order.status = "completed"
        order.save(update_fields=["tx_hash", "status"])

        # Return JSON response
        return JsonResponse({
            "success": True,
            "crypto_name": order.crypto.name,
            "crypto_symbol": order.crypto.symbol,
            "crypto_amount": str(order.crypto_amount),
            "total_ngn_charged": str(order.total_price),
            "wallet_address": order.wallet_address,
            "tx_hash": order.tx_hash,
            "created_at": order.created_at.isoformat(),
        })

    # GET: render template (price via WebSocket)
    return render(request, "gasfee/buy_crypto.html", {
        "crypto": crypto,
        "exchange_rate": exchange_rate,
        "crypto_price": crypto_price,
    })

    

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
