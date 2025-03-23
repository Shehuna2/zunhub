import requests
import logging

from django.core.cache import cache
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from decimal import Decimal
from django.contrib import messages
from django.utils import timezone
from web3 import Web3
from .utils import send_order_email

from p2p.models import Wallet
from .models import CryptoPurchase, Crypto, ExchangeRateMargin
from .tasks import process_crypto_order



logger = logging.getLogger(__name__)



@login_required
def buy_crypto(request, crypto_id):
    crypto = get_object_or_404(Crypto, id=crypto_id)

    # Cache keys
    crypto_price_key = f"crypto_price_{crypto.coingecko_id}_usd"  # Updated to usd
    exchange_rate_key = "exchange_rate_usdt_ngn"

    # Fetch live crypto price (e.g., TON in USD) from cache or API
    crypto_price = cache.get(crypto_price_key)
    if crypto_price is None:
        crypto_price_url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto.coingecko_id}&vs_currencies=usd"
        logger.info(f"Fetching crypto price from: {crypto_price_url}")
        try:
            response = requests.get(crypto_price_url, timeout=5)
            response.raise_for_status()
            crypto_price_data = response.json()
            logger.info(f"Crypto price raw response: {crypto_price_data}")
            if not crypto_price_data or crypto.coingecko_id not in crypto_price_data:
                raise ValueError(f"No price data for {crypto.coingecko_id}")
            price_dict = crypto_price_data[crypto.coingecko_id]
            if "usd" not in price_dict or not price_dict["usd"]:  # Changed to usd
                raise ValueError(f"USD price missing or invalid for {crypto.coingecko_id}")
            crypto_price = Decimal(str(price_dict["usd"]))  # Changed to usd
            cache.set(crypto_price_key, crypto_price, timeout=300)
            logger.info(f"Cached crypto price for {crypto.coingecko_id}: {crypto_price}")
        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            crypto_price = Decimal("500")  # Fallback
            messages.warning(request, "Couldn’t fetch live crypto price. Using fallback value.")
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Data parsing error: {str(e)}, Response: {crypto_price_data}")
            crypto_price = Decimal("500")  # Fallback
            messages.warning(request, "Couldn’t fetch live crypto price. Using fallback value.")
    else:
        logger.info(f"Using cached crypto price for {crypto.coingecko_id}: {crypto_price}")

    # Fetch live USDT/NGN exchange rate from cache or API
    base_exchange_rate = cache.get(exchange_rate_key)
    if base_exchange_rate is None:
        exchange_rate_url = "https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=ngn"
        logger.info(f"Fetching exchange rate from: {exchange_rate_url}")
        try:
            response = requests.get(exchange_rate_url, timeout=5)
            response.raise_for_status()
            exchange_rate_data = response.json()
            logger.info(f"Exchange rate raw response: {exchange_rate_data}")
            if "tether" not in exchange_rate_data or "ngn" not in exchange_rate_data["tether"]:
                raise ValueError("NGN price missing for tether")
            base_exchange_rate = Decimal(str(exchange_rate_data["tether"]["ngn"]))
            cache.set(exchange_rate_key, base_exchange_rate, timeout=300)
            logger.info(f"Cached exchange rate: {base_exchange_rate}")
        except (requests.RequestException, KeyError, ValueError) as e:
            logger.error(f"Failed to fetch exchange rate: {str(e)}")
            base_exchange_rate = Decimal("1500")
            messages.warning(request, "Couldn’t fetch live exchange rate. Using default value.")
    else:
        logger.info(f"Using cached exchange rate: {base_exchange_rate}")

    # Apply profit margin
    try:
        margin = ExchangeRateMargin.objects.get(currency_pair="USDT/NGN").profit_margin
    except ExchangeRateMargin.DoesNotExist:
        margin = Decimal("0")
    exchange_rate = base_exchange_rate + margin

    if request.method == "POST":
        wallet_address = request.POST.get("wallet_address")
        amount = Decimal(request.POST.get("amount", "0"))
        currency = request.POST.get("currency", "ngn").upper()

        if amount <= 0:
            return JsonResponse({"success": False, "error": "Invalid amount."})

        crypto_received = Decimal("0")
        total_price_ngn = Decimal("0")

        if currency == "NGN":
            amount_in_usd = amount / exchange_rate  # Changed to usd conceptually
            crypto_received = amount_in_usd / crypto_price
            total_price_ngn = amount
        elif currency == "USDT":  # Treat as USD for simplicity
            crypto_received = amount / crypto_price
            total_price_ngn = amount * exchange_rate
        elif currency == crypto.symbol.upper():
            crypto_received = amount
            total_price_ngn = (amount * crypto_price) * exchange_rate
        else:
            return JsonResponse({"success": False, "error": "Invalid currency selection."})

        wallet = Wallet.objects.get(user=request.user)
        if wallet.balance < total_price_ngn:
            return JsonResponse({"success": False, "error": "Insufficient balance."})

        wallet.balance -= total_price_ngn
        wallet.save()

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

        process_crypto_order.delay(order.id)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "success": True,
                "message": f"Your {crypto_received:.6f} {crypto.symbol} purchase is processing."
            })

        messages.success(request, f"Your order for {crypto_received:.6f} {crypto.symbol} is being processed!")
        return redirect("asset_list")

    return render(request, "gasfee/buy_crypto.html", {
        "crypto": crypto,
        "exchange_rate": exchange_rate,
        "crypto_price": crypto_price,
    })



def asset_list(request):
    cryptos = Crypto.objects.all()

    return render(request, "gasfee/crypto_list.html", {"cryptos": cryptos})



# Connect to Ethereum Network (Replace with Binance Smart Chain, Polygon, etc.)
WEB3_PROVIDER = "https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID"
web3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

PRIVATE_KEY = "YOUR_WALLET_PRIVATE_KEY"  # The wallet that will send the crypto
SENDER_WALLET = "YOUR_WALLET_ADDRESS"

def send_crypto(order):
    """Send crypto to user using Web3"""
    try:
        amount_wei = web3.to_wei(order.amount, 'ether')  # Convert to smallest unit
        nonce = web3.eth.get_transaction_count(SENDER_WALLET)

        txn = {
            'to': order.wallet_address,
            'value': amount_wei,
            'gas': 21000,
            'gasPrice': web3.to_wei('10', 'gwei'),
            'nonce': nonce,
            'chainId': 1  # Mainnet (Change for Testnet)
        }

        signed_txn = web3.eth.account.sign_transaction(txn, PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        order.transaction_hash = web3.to_hex(tx_hash)
        order.status = "completed"
        order.settled_at = timezone.now()
        order.save()

        send_order_email()

        return True
    except Exception as e:
        print(f"Transaction failed: {e}")
        order.status = "failed"
        order.save()
        return False


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
