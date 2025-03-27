import os
import time
import requests
import logging
import traceback
from decimal import Decimal
from django.core.cache import cache
from tonsdk.contract.wallet import WalletVersionEnum, Wallets
from tonsdk.provider import ToncenterClient
from tonsdk.utils import to_nano
from web3 import Web3
from dotenv import load_dotenv

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

# ✅ TON Setup using tonsdk.py
TON_API_URL = get_env_var("TON_API_URL")
ton_client = ToncenterClient(base_url=TON_API_URL, api_key=get_env_var("TONCENTER_API_KEY"))
SENDER_SEED = get_env_var("TON_SEED_PHRASE")

# ✅ Properly load wallet from mnemonic
_, _, _, wallet = Wallets.from_mnemonics(SENDER_SEED.split(), WalletVersionEnum.v3r2, workchain=0)
SENDER_ADDRESS = wallet.address.to_string(True, True, True)


logger.info(f"Derived TON Wallet Address: {SENDER_ADDRESS}")

# ✅ TON Wallet Validation Function
def is_valid_ton_wallet(address):
    """Validate if a given TON wallet address is valid"""
    if not address:
        return False
    try:
        unpack_url = f"https://toncenter.com/api/v2/unpackAddress?address={address}"
        response = requests.get(unpack_url, headers={"accept": "application/json"})
        return response.status_code == 200 and response.json().get("ok", False)
    except Exception as e:
        logger.error(f"TON wallet validation failed: {e}")
        return False

# ✅ Send TON Function using tonsdk.py
def send_ton(wallet_address, amount):
    try:
        # Validate wallet address before sending
        if not is_valid_ton_wallet(wallet_address):
            logger.error(f"Invalid TON wallet address: {wallet_address}")
            return None

        nanotons = to_nano(amount, "ton")  # Convert TON to nanotons

        # Get seqno from TON blockchain
        seqno = ton_client.get_seqno(SENDER_ADDRESS)
        if seqno is None:
            logger.error(f"Failed to retrieve seqno for wallet: {SENDER_ADDRESS}")
            return None

        # Create transaction message with seqno
        tx = wallet.create_transfer_message(wallet_address, nanotons, seqno)

        # Sign the transaction before sending
        signed_boc = wallet.sign(tx["message"].to_boc(False))

        # Send the signed transaction
        result = ton_client.send_boc(signed_boc)

        if 'result' not in result:
            logger.error(f"Transaction submission failed: {result}")
            return None

        tx_hash = result['result']
        logger.info(f"Transaction Sent! Hash: {tx_hash}")

        # Verify that the transaction appears on the blockchain
        for _ in range(10):  # Retry up to 10 times with a delay
            time.sleep(5)  # Wait 5 seconds before checking
            tx_status = ton_client.get_transactions(SENDER_ADDRESS, limit=1)

            if tx_status and tx_status[0]['transaction_id']['hash'] == tx_hash:
                logger.info(f"Transaction {tx_hash} confirmed on blockchain!")
                return tx_hash

        logger.warning(f"Transaction {tx_hash} was sent but not confirmed after multiple checks.")
        return None

    except Exception as e:
        logger.error(f"Failed to send TON transaction: {e}\n{traceback.format_exc()}")
        return None




# ✅ BSC Setup
BSC_RPC_URL = get_env_var("BSC_RPC_URL")
w3 = Web3(Web3.HTTPProvider(BSC_RPC_URL))

if not w3.is_connected():
    raise ConnectionError(f"Failed to connect to BSC RPC: {BSC_RPC_URL}")

BSC_SENDER_PRIVATE_KEY = get_env_var("BSC_SENDER_PRIVATE_KEY")
BSC_SENDER_ADDRESS = w3.eth.account.from_key(BSC_SENDER_PRIVATE_KEY).address

# ✅ Send BSC Transaction Function
def send_bsc(to_address, amount):
    if not Web3.is_address(to_address):
        raise ValueError(f"Invalid BSC wallet address: {to_address}")

    try:
        to_address = Web3.to_checksum_address(to_address)
        value = w3.to_wei(amount, 'ether')
        gas_price = w3.eth.gas_price
        gas_limit = 21000  # Standard gas limit for BNB transfer
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


# Function to get crypto price with cache
def get_crypto_price(coingecko_id):
    crypto_price_key = f"crypto_price_{coingecko_id}"
    crypto_price = cache.get(crypto_price_key)

    if crypto_price is None:
        crypto_price_url = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd"
        logger.info(f"Fetching crypto price from: {crypto_price_url}")

        try:
            response = requests.get(crypto_price_url, timeout=5)
            response.raise_for_status()
            crypto_price_data = response.json()

            if coingecko_id not in crypto_price_data or "usd" not in crypto_price_data[coingecko_id]:
                raise ValueError(f"No valid price data for {coingecko_id}")

            crypto_price = Decimal(str(crypto_price_data[coingecko_id]["usd"]))
            cache.set(crypto_price_key, crypto_price, timeout=300)  # Cache for 5 minutes
            logger.info(f"Cached crypto price for {coingecko_id}: {crypto_price}")

        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}\n{traceback.format_exc()}")
            crypto_price = Decimal("500")  # Fallback value
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Data parsing error: {str(e)}\n{traceback.format_exc()}")
            crypto_price = Decimal("500")  # Fallback value
    else:
        logger.info(f"Using cached crypto price for {coingecko_id}: {crypto_price}")

    return crypto_price

# ✅ Fully Restored: Function to get USD to NGN exchange rate
def get_exchange_rate():
    exchange_rate_key = "exchange_rate_usd_ngn"
    base_exchange_rate = cache.get(exchange_rate_key)

    if base_exchange_rate is None:
        exchange_rate_url = "https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=ngn"
        logger.info(f"Fetching exchange rate from: {exchange_rate_url}")

        try:
            response = requests.get(exchange_rate_url, timeout=5)
            response.raise_for_status()
            exchange_rate_data = response.json()

            if "tether" not in exchange_rate_data or "ngn" not in exchange_rate_data["tether"]:
                raise ValueError("NGN price missing for tether")

            base_exchange_rate = Decimal(str(exchange_rate_data["tether"]["ngn"]))
            cache.set(exchange_rate_key, base_exchange_rate, timeout=300)  # Cache for 5 minutes
            logger.info(f"Cached exchange rate: {base_exchange_rate}")

        except (requests.RequestException, KeyError, ValueError) as e:
            logger.error(f"Failed to fetch exchange rate: {str(e)}\n{traceback.format_exc()}")
            base_exchange_rate = Decimal("1500")  # Fallback value
    else:
        logger.info(f"Using cached exchange rate: {base_exchange_rate}")

    try:
        from .models import ExchangeRateMargin
        margin = ExchangeRateMargin.objects.get(currency_pair="USDT/NGN").profit_margin
    except ExchangeRateMargin.DoesNotExist:
        margin = Decimal("0")

    return base_exchange_rate + margin