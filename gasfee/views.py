import os
import requests
import logging
import traceback
import base58
from decimal import Decimal
from django.conf import settings



from django.core.cache import cache
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from django.contrib import messages
from web3 import Web3
from dotenv import load_dotenv



from p2p.models import Wallet
from .models import CryptoPurchase, Crypto
from .utils import (
    get_crypto_price, get_exchange_rate, send_bsc, check_solana_balance, 
    send_evm, send_solana, validate_solana_address, send_ton, validate_ton_address
)
from .near_utils import (
    validate_near_account_id, send_near
)




# Load environment variables
load_dotenv()
logger = logging.getLogger(__name__)



def asset_list(request):
    """Returns a list of available crypto assets with live prices and logos."""
    cryptos = Crypto.objects.all()
    crypto_list = []

    # Collect all CoinGecko IDs for a single API call
    coingecko_ids = [crypto.coingecko_id for crypto in cryptos]
    network_map = {crypto.coingecko_id: getattr(crypto, 'network', 'Ethereum').lower() for crypto in cryptos}

    # Fetch prices in batch
    prices = {}
    cache_key = f"crypto_prices_{'_'.join(sorted(coingecko_ids))}"
    cached_prices = cache.get(cache_key)

    if cached_prices is None:
        try:
            # Batch request to CoinGecko
            ids_param = ','.join(coingecko_ids)
            response = requests.get(
                f"https://api.coingecko.com/api/v3/simple/price?ids={ids_param}&vs_currencies=usd"
            )
            response.raise_for_status()
            prices = response.json()
            cache.set(cache_key, prices, timeout=300)  # Cache for 5 minutes
        except Exception as e:
            logger.error(f"Failed to fetch batch prices: {e}")
            prices = {}
    else:
        prices = cached_prices

    for crypto in cryptos:
        # Get price from batch response
        price = prices.get(crypto.coingecko_id, {}).get('usd', 0)
        if price == 0:
            # Fallback to individual fetch if needed (with rate limit handling)
            individual_cache_key = f"crypto_price_{crypto.coingecko_id}_{network_map[crypto.coingecko_id]}"
            price = cache.get(individual_cache_key)
            if price is None:
                try:
                    price = get_crypto_price(crypto.coingecko_id, network_map[crypto.coingecko_id])
                    cache.set(individual_cache_key, price, timeout=300)
                except Exception as e:
                    logger.error(f"Failed to fetch price for {crypto.coingecko_id}: {e}")
                    price = 0

        # Use logo_url from model, fallback to placeholder
        logo_url = getattr(crypto, 'logo_url', None)
        if not logo_url:
            logo_url = f"{settings.MEDIA_URL}images/default_crypto_logo.png"  # Ensure this file exists

        crypto_list.append({
            'id': crypto.id,
            'name': crypto.name,
            'symbol': crypto.symbol,
            'coingecko_id': crypto.coingecko_id,
            'price': price,
            'logo_url': crypto.logo.url,
        })

    return render(request, "gasfee/crypto_list.html", {"cryptos": crypto_list})


@login_required
def buy_crypto(request, crypto_id):
    crypto = get_object_or_404(Crypto, id=crypto_id)
    logger.info(f"Crypto Symbol: {crypto.symbol}, Upper: {crypto.symbol.upper()}")

    # Fetch cached prices
    network = crypto.network if hasattr(crypto, "network") else "Ethereum"
    crypto_price = cache.get(f"crypto_price_{crypto.coingecko_id}_{network.lower()}")
    exchange_rate = cache.get("exchange_rate_usd_ngn")

    if crypto_price is None:
        crypto_price = get_crypto_price(crypto.coingecko_id, network)
        cache.set(f"crypto_price_{crypto.coingecko_id}_{network.lower()}", crypto_price, timeout=300)

    if exchange_rate is None:
        exchange_rate = get_exchange_rate()
        cache.set("exchange_rate_usd_ngn", exchange_rate, timeout=300)

    if request.method == "POST":
        wallet_address = request.POST.get("wallet_address")

        try:
            amount = Decimal(request.POST.get("amount", "0"))
            if amount <= 0:
                raise ValueError("Invalid amount")

            currency = request.POST.get("currency", "NGN").upper()

            # Convert amount to crypto received
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
            
            logger.info(f"Processing purchase: {amount} {currency} for {crypto_received:.6f} {crypto.symbol} to {wallet_address}")

            # Handle rent/deployment costs within atomic transaction
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=request.user)
                total_ngn_deducted = total_price_ngn
                
                if crypto.symbol.upper() == "SOL":
                    receiver_balance = check_solana_balance(wallet_address)
                    rent_exemption = Decimal('0.00089')
                    rent_sol = rent_exemption if receiver_balance == 0 else Decimal('0')
                    rent_ngn = (rent_sol * crypto_price * exchange_rate).quantize(Decimal('0.01'))
                    total_ngn_deducted += rent_ngn
                elif crypto.symbol.upper() == "TON":
                    # Assume max deployment cost upfront
                    deployment_ton = Decimal('0.05')  # Match utils.py
                    deployment_ngn = (deployment_ton * crypto_price * exchange_rate).quantize(Decimal('0.01'))
                    total_ngn_deducted += deployment_ngn
                else:
                    rent_sol = Decimal('0')  # No rent/deployment for others
                
                if wallet.balance < total_ngn_deducted:
                    return JsonResponse({
                        "success": False,
                        "error": f"Insufficient NGN balance. Required: {total_ngn_deducted}, Available: {wallet.balance}"
                    })

                wallet.balance -= total_ngn_deducted
                wallet.save(update_fields=["balance"])

                order = CryptoPurchase.objects.create(
                    user=request.user,
                    crypto=crypto,
                    input_amount=amount,
                    input_currency=currency,
                    crypto_amount=crypto_received,
                    total_price=total_ngn_deducted,  # Includes potential deployment/rent
                    wallet_address=wallet_address,
                    status="pending"
                )

            # Validate wallet address
            if crypto.symbol.upper() == "BNB" or "ETH" in crypto.symbol.upper():
                try:
                    wallet_address = Web3.to_checksum_address(wallet_address)
                except ValueError:
                    return JsonResponse({"success": False, "error": "Invalid Ethereum address format."})
            elif crypto.symbol.upper() == "SOL":
                if not validate_solana_address(wallet_address):
                    logger.warning(f"Invalid Solana address: {wallet_address}")
                    return JsonResponse({"success": False, "error": "Invalid Solana address format."})
                logger.info(f"Valid Solana address: {wallet_address}")
            elif crypto.symbol.upper() == "NEAR":
                if not validate_near_account_id(wallet_address):
                    logger.warning(f"Invalid NEAR address: {wallet_address}")
                    return JsonResponse({"success": False, "error": "Invalid NEAR address format."})
                logger.info(f"Valid NEAR address: {wallet_address}")
            elif crypto.symbol.upper() == "TON":
                if not validate_ton_address(wallet_address):
                    logger.warning(f"Invalid TON address: {wallet_address}")
                    return JsonResponse({"success": False, "error": "Invalid TON address format."})
                logger.info(f"Valid TON address: {wallet_address}")
            else:
                return JsonResponse({"success": False, "error": "Unsupported token."})

            # Handle transaction
            try:
                logger.info(f"Attempting transfer for symbol: {crypto.symbol.upper()}")
                if crypto.symbol.upper() == "BNB":
                    tx_hash = send_bsc(wallet_address, crypto_received)
                elif crypto.symbol.upper() == "SOL":
                    tx_hash, actual_rent_sol = send_solana(wallet_address, float(crypto_received))
                    if Decimal(str(actual_rent_sol)) != rent_sol:
                        logger.warning(f"Rent mismatch: expected {rent_sol}, sent {actual_rent_sol}")
                elif crypto.symbol.upper() == "TON":
                    tx_hash, actual_deployment_ton = send_ton(wallet_address, float(crypto_received), order.id)
                    logger.info(f"Transaction hash from send_ton: {tx_hash}")  
                    # Adjust if deployment wasn’t needed
                    if actual_deployment_ton == 0:
                        refund_amount = deployment_ngn
                        wallet.balance += refund_amount
                        wallet.save(update_fields=["balance"])
                        total_ngn_deducted -= refund_amount
                        order.total_price = total_ngn_deducted
                        order.save(update_fields=["total_price"])
                elif crypto.symbol.upper() == "NEAR":
                    if not validate_near_account_id(wallet_address):
                        return JsonResponse({"success": False, "error": "Invalid NEAR account ID format."})
                    try:
                        tx_hash = send_near(wallet_address, crypto_received)
                        logger.info(f"NEAR transaction hash: {tx_hash}")
                    except ValueError as e:
                        return JsonResponse({"success": False, "error": str(e)})
                elif "ETH" in crypto.symbol.upper():
                    evm_network = crypto.symbol.split("-")[-1]
                    tx_hash = send_evm(evm_network, wallet_address, Web3.to_wei(crypto_received, "ether"))
                else:
                    return JsonResponse({"success": False, "error": "Unsupported token."})

                order.tx_hash = tx_hash
                order.status = "completed"
                order.save(update_fields=["tx_hash", "status"])

                message = f"Your {crypto_received:.6f} {crypto.symbol} has been sent!"
                if crypto.symbol.upper() == "SOL" and rent_sol > 0:
                    message += f" (includes {rent_sol:.6f} SOL rent for unfunded wallet)"
                elif crypto.symbol.upper() == "TON" and actual_deployment_ton > 0:
                    message += f" (includes {actual_deployment_ton:.6f} TON for wallet deployment)"

                return JsonResponse({
                    "success": True,
                    "message": message,
                    "tx_hash": tx_hash,
                    "total_ngn_charged": str(total_ngn_deducted)
                })
            except Exception as tx_error:
                logger.error(f"Crypto transfer failed: {tx_error}\n{traceback.format_exc()}")
                refund_user(request, order)
                return JsonResponse({"success": False, "error": "Transaction failed. Refund issued."})

        except (ValueError, TypeError):
            return JsonResponse({"success": False, "error": "Invalid amount input."})

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
