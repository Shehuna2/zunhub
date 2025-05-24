import os
import json 
import time
import base58
import base64
import requests
import logging
import traceback
from decimal import Decimal
from django.core.cache import cache
from django.conf import settings
from web3 import Web3
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests.exceptions
from requests.exceptions import HTTPError



# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Validate essential environment variables
def get_env_var(var_name, required=True):
    value = os.getenv(var_name)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {var_name}")
    return value

# BSC setup (unchanged)
BSC_RPC_URL = get_env_var("BSC_RPC_URL")
w3 = Web3(Web3.HTTPProvider(BSC_RPC_URL))

if not w3.is_connected():
    raise ConnectionError(f"Failed to connect to BSC RPC: {BSC_RPC_URL}")

BSC_SENDER_PRIVATE_KEY = get_env_var("BSC_SENDER_PRIVATE_KEY")
BSC_SENDER_ADDRESS = w3.eth.account.from_key(BSC_SENDER_PRIVATE_KEY).address


# EVM setup (unchanged)
ARBITRUM_RPC = os.getenv("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc")
BASE_RPC = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
OPTIMISM_RPC = os.getenv("OPTIMISM_RPC_URL", "https://mainnet.optimism.io")
L2_CHAINS = {
    "ARB": {"rpc": ARBITRUM_RPC, "symbol": "ETH"},
    "BASE": {"rpc": BASE_RPC, "symbol": "ETH"},
    "OP": {"rpc": OPTIMISM_RPC, "symbol": "ETH"}
}

def send_evm(chain, recipient, amount_wei):
    if chain not in L2_CHAINS:
        raise ValueError(f"Unsupported chain: {chain}")
    w3 = Web3(Web3.HTTPProvider(L2_CHAINS[chain]["rpc"]))
    sender_private_key = os.getenv(f"{chain}_PRIVATE_KEY")
    sender_address = os.getenv(f"{chain}_SENDER_ADDRESS")
    sender_address = Web3.to_checksum_address(sender_address)
    recipient = Web3.to_checksum_address(recipient)
    if not sender_private_key or not sender_address:
        raise ValueError("Sender wallet not configured for " + chain)
    sender_balance = w3.eth.get_balance(sender_address)
    nonce = w3.eth.get_transaction_count(sender_address)
    gas_price = w3.eth.gas_price
    tx_estimate = {
        "from": sender_address,
        "to": recipient,
        "value": amount_wei,
        "gasPrice": gas_price,
        "nonce": nonce,
        "chainId": w3.eth.chain_id
    }
    try:
        gas_limit = w3.eth.estimate_gas(tx_estimate)
    except Exception as e:
        raise ValueError(f"Gas estimation failed: {str(e)}")
    total_cost = amount_wei + (gas_limit * gas_price)
    if sender_balance < total_cost:
        raise ValueError(f"Insufficient balance on {chain}. Required: {w3.from_wei(total_cost, 'ether')} ETH, Available: {w3.from_wei(sender_balance, 'ether')} ETH")
    tx = {
        "to": recipient,
        "value": amount_wei,
        "gas": gas_limit,
        "gasPrice": gas_price,
        "nonce": nonce,
        "chainId": w3.eth.chain_id
    }
    signed_tx = w3.eth.account.sign_transaction(tx, sender_private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    return w3.to_hex(tx_hash)


def send_bsc(to_address, amount):
    if not Web3.is_address(to_address):
        raise ValueError(f"Invalid BSC wallet address: {to_address}")
    try:
        to_address = Web3.to_checksum_address(to_address)
        value = w3.to_wei(amount, 'ether')
        gas_price = w3.eth.gas_price
        gas_limit = 21000
        tx_cost = gas_limit * gas_price
        sender_balance = w3.eth.get_balance(BSC_SENDER_ADDRESS)
        if sender_balance < (value + tx_cost):
            raise ValueError(f"Insufficient BNB balance.")
        nonce = w3.eth.get_transaction_count(BSC_SENDER_ADDRESS)
        tx = {
            'nonce': nonce,
            'to': to_address,
            'value': value,
            'gas': gas_limit,
            'gasPrice': gas_price,
            'chainId': 56
        }
        signed_tx = w3.eth.account.sign_transaction(tx, BSC_SENDER_PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return tx_hash.hex()
    except Exception as e:
        logger.error(f"Failed to send BSC transaction: {str(e)}\n{traceback.format_exc()}")
        raise

def get_crypto_price(coingecko_id, network="Ethereum"):
    # key for fresh price (expires in 5 minutes)
    fresh_key = f"crypto_price_{coingecko_id}_{network.lower()}"
    # key for last known price (never expires)
    last_known_key = f"crypto_price_last_known_{coingecko_id}_{network.lower()}"

    # 1) Try the fresh cache
    crypto_price = cache.get(fresh_key)
    if crypto_price is not None:
        logger.info(f"Using fresh cached price for {coingecko_id} on {network}: {crypto_price}")
        return crypto_price

    # 2) Fresh cache miss → attempt API fetch
    url = (
        f"https://api.coingecko.com/api/v3/simple/price"
        f"?ids={coingecko_id}&vs_currencies=usd"
    )
    logger.info(f"Fetching crypto price for {network} from: {url}")
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        usd_price = data[coingecko_id]["usd"]
        crypto_price = Decimal(str(usd_price))

        # update both caches
        cache.set(fresh_key, crypto_price, timeout=300)       # 5 min
        cache.set(last_known_key, crypto_price, timeout=None) # never expire

        logger.info(f"Cached fresh price for {coingecko_id}: {crypto_price}")
        return crypto_price

    except requests.RequestException as e:
        logger.error(
            f"API request failed for {coingecko_id} on {network}: {e}\n"
            + traceback.format_exc()
        )
    except (KeyError, ValueError, TypeError) as e:
        logger.error(
            f"Data parsing error for {coingecko_id} on {network}: {e}\n"
            + traceback.format_exc()
        )

    # 3) On *any* failure, try the fresh cache one more time (maybe race)…
    crypto_price = cache.get(fresh_key)
    if crypto_price is not None:
        logger.info(f"Using just‐set fresh cache after error for {coingecko_id}: {crypto_price}")
        return crypto_price

    # 4) …then try the “last known” cache
    crypto_price = cache.get(last_known_key)
    if crypto_price is not None:
        logger.info(f"Using last‐known cached price for {coingecko_id}: {crypto_price}")
        return crypto_price

    # 5) Finally, give up and use hard‑coded default
    logger.warning(
        f"No cached price available for {coingecko_id}; falling back to 500"
    )
    return Decimal("500")

def get_exchange_rate():
    # 1) Keys: fresh (5 min) and last‑known (never expire)
    fresh_key     = "exchange_rate_usd_ngn"
    last_known_key = "exchange_rate_last_known_usd_ngn"

    # 2) Try fresh cache
    rate = cache.get(fresh_key)
    if rate is not None:
        logger.info(f"Using fresh cached USD→NGN rate: {rate}")
    else:
        # 3) Fetch from Coingecko
        url = (
            "https://api.coingecko.com/api/v3/simple/price"
            "?ids=tether&vs_currencies=ngn"
        )
        logger.info(f"Fetching USD→NGN rate from: {url}")
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            ngn_price = data["tether"]["ngn"]
            rate = Decimal(str(ngn_price))

            # update both caches
            cache.set(fresh_key, rate, timeout=300)       # 5 min
            cache.set(last_known_key, rate, timeout=None) # never expire

            logger.info(f"Cached fresh USD→NGN rate: {rate}")

        except (requests.RequestException, KeyError, ValueError) as e:
            logger.error(
                f"Failed to fetch USD→NGN rate: {e}\n"
                + traceback.format_exc()
            )

            # 4) On error, re‑check fresh cache (race)…
            rate = cache.get(fresh_key)
            if rate is not None:
                logger.info(
                    f"Using just‑set fresh cache after error: {rate}"
                )
            else:
                # 5) …then fall back to last‑known
                rate = cache.get(last_known_key)
                if rate is not None:
                    logger.info(f"Using last‑known USD→NGN rate: {rate}")
                else:
                    # 6) Ultimate default
                    rate = Decimal("1500")
                    logger.warning(
                        "No cached USD→NGN rate available; falling back to 1500"
                    )

    # 7) Apply your margin
    try:
        from .models import ExchangeRateMargin
        margin = ExchangeRateMargin.objects.get(
            currency_pair="USDT/NGN"
        ).profit_margin
    except ExchangeRateMargin.DoesNotExist:
        margin = Decimal("0")
    return rate + margin