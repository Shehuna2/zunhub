import requests
from django.core.cache import cache
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from decimal import Decimal
from django.contrib import messages
from django.utils import timezone
from web3 import Web3
from .utils import get_usdt_ngn_rate, send_order_email

from p2p.models import Wallet
from .models import CryptoPurchase, Crypto
from .tasks import process_crypto_order


def asset_list(request):
    cryptos = Crypto.objects.all()

    return render(request, "gasfee/crypto_list.html", {"cryptos": cryptos})



from decimal import Decimal

@login_required
def buy_crypto(request, crypto_id):
    crypto = get_object_or_404(Crypto, id=crypto_id)
    exchange_rate = Decimal(str(get_usdt_ngn_rate()))  # NGN per USDT

    if request.method == "POST":
        wallet_address = request.POST.get("wallet_address")
        amount = Decimal(request.POST.get("amount", "0"))
        currency = request.POST.get("currency", "ngn").upper()

        if amount <= 0:
            return JsonResponse({"success": False, "error": "Invalid amount."})

        crypto_price = Decimal(str(crypto.price_rate))  # USDT per crypto unit
        crypto_received = Decimal("0")
        total_price_ngn = Decimal("0")

        if currency == "NGN":
            # NGN -> USDT -> Crypto
            amount_in_usdt = amount / exchange_rate
            crypto_received = amount_in_usdt / crypto_price
            total_price_ngn = amount
        elif currency == "USDT":
            # USDT -> Crypto -> NGN
            crypto_received = amount / crypto_price
            total_price_ngn = amount * exchange_rate
        elif currency == crypto.symbol.upper():
            # Crypto -> USDT -> NGN
            crypto_received = amount
            total_price_ngn = (amount * crypto_price) * exchange_rate
        else:
            return JsonResponse({"success": False, "error": "Invalid currency selection."})

        wallet = Wallet.objects.get(user=request.user)

        if wallet.balance < total_price_ngn:
            return JsonResponse({"success": False, "error": "Insufficient balance."})

        wallet.balance -= total_price_ngn  # Deduct in NGN
        wallet.save()

        order = CryptoPurchase.objects.create(
            user=request.user,
            crypto=crypto,
            input_amount=amount,
            input_currency=currency,
            crypto_amount=crypto_received,
            total_price=total_price_ngn,  # In NGN
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
    })


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
