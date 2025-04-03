import os
import time
import base58
import requests
import logging
import traceback
from decimal import Decimal
from django.core.cache import cache
from web3 import Web3
from dotenv import load_dotenv

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.api import Client
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction
from solders.message import Message

# TON-specific imports
from tonsdk.contract.wallet import Wallets, WalletVersionEnum
from tonsdk.utils import to_nano, Address

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


# Solana setup (unchanged)
SOLANA_PRIVATE_KEY_B58 = get_env_var("SOLANA_PRIVATE_KEY", required=True).strip('"')
SOLANA_RPC_URL = get_env_var("SOLANA_RPC_URL", required=True)
SOLANA_SENDER_KEYPAIR = Keypair.from_bytes(base58.b58decode(SOLANA_PRIVATE_KEY_B58))

solana_client = Client(SOLANA_RPC_URL)

if not SOLANA_PRIVATE_KEY_B58:
    raise ValueError("SOLANA_PRIVATE_KEY is empty")
try:
    decoded_key = base58.b58decode(SOLANA_PRIVATE_KEY_B58)
    SOLANA_SENDER_KEYPAIR = Keypair.from_bytes(decoded_key)
except Exception as e:
    logger.error(f"Invalid SOLANA_PRIVATE_KEY: {e}")
    raise ValueError(f"Invalid SOLANA_PRIVATE_KEY format: {e}")

# TON setup
TON_MNEMONIC = get_env_var("TON_MNEMONIC", required=True).split()
TON_API_URL = "https://toncenter.com/api/v2/jsonRPC"

if len(TON_MNEMONIC) != 24:
    raise ValueError(f"TON_MNEMONIC must contain exactly 24 words, got {len(TON_MNEMONIC)}")

# Create TON wallet with correct unpacking
mnemonics_returned, pub_k, priv_k, TON_SENDER_WALLET = Wallets.from_mnemonics(
    mnemonics=TON_MNEMONIC,
    version=WalletVersionEnum.v3r2,
    workchain=0
)
TON_SENDER_ADDRESS = TON_SENDER_WALLET.address.to_string(True, True, True)
logger.info(f"TON Sender Address: {TON_SENDER_ADDRESS}")

# Solana functions (unchanged)
def check_solana_balance(wallet_address) -> float:
    try:
        if isinstance(wallet_address, Pubkey):
            pubkey = wallet_address
        else:
            pubkey = Pubkey.from_string(wallet_address)
        balance = solana_client.get_balance(pubkey)
        sol_balance = balance.value / 1_000_000_000
        if sol_balance < 0:
            raise ValueError(f"Insufficient balance: {sol_balance} SOL")
        logger.info(f"Balance for {pubkey}: {sol_balance} SOL")
        return sol_balance
    except Exception as e:
        logger.error(f"Failed to fetch balance for {pubkey}: {e}")
        raise ValueError(f"Failed to fetch balance: {e}")

def validate_solana_address(wallet_address: str) -> bool:
    try:
        Pubkey.from_string(wallet_address)
        return True
    except Exception:
        return False

def send_solana(receiver_address: str, purchase_sol: float) -> tuple[str, float]:
    logger.info(f"Initiating SOL transfer: {purchase_sol} SOL -> {receiver_address}")
    if not validate_solana_address(receiver_address):
        raise ValueError(f"Invalid receiver address: {receiver_address}")
    sender_pubkey = SOLANA_SENDER_KEYPAIR.pubkey()
    sender_balance = check_solana_balance(str(sender_pubkey))
    receiver_balance = check_solana_balance(receiver_address)
    rent_exemption = 0.00089
    rent_sol = rent_exemption if receiver_balance == 0 else 0
    total_sol = purchase_sol + rent_sol
    if sender_balance < total_sol:
        raise ValueError(f"Insufficient balance: {sender_balance} SOL, need {total_sol} SOL")
    try:
        receiver_pubkey = Pubkey.from_string(receiver_address)
        transfer_ix = transfer(TransferParams(
            from_pubkey=sender_pubkey,
            to_pubkey=receiver_pubkey,
            lamports=int(total_sol * 1_000_000_000)
        ))
        blockhash_resp = solana_client.get_latest_blockhash()
        recent_blockhash = blockhash_resp.value.blockhash
        msg = Message.new_with_blockhash(
            instructions=[transfer_ix],
            payer=sender_pubkey,
            blockhash=recent_blockhash
        )
        txn = Transaction(
            from_keypairs=[SOLANA_SENDER_KEYPAIR],
            message=msg,
            recent_blockhash=recent_blockhash
        )
        result = solana_client.send_transaction(txn)
        tx_signature = str(result.value)
        logger.info(f"Solana transaction successful: {tx_signature}")
        return tx_signature, rent_sol
    except Exception as e:
        logger.error(f"Transaction failed: {e}\n{traceback.format_exc()}")
        raise ValueError(f"Transaction failed: {e}")

# TON-specific functions
def check_ton_balance(address: str) -> float:
    """Check the TON balance of an address."""
    try:
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "getAddressBalance",
            "params": {"address": address}
        }
        response = requests.post(TON_API_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        if 'result' in result:
            balance = int(result['result']) / 1_000_000_000  # TON uses 9 decimals
            logger.info(f"Balance for {address}: {balance} TON")
            return balance
        raise ValueError("No balance data in response")
    except Exception as e:
        logger.error(f"Failed to fetch TON balance for {address}: {e}")
        raise ValueError(f"Failed to fetch TON balance: {e}")

def validate_ton_address(address: str) -> bool:
    """Validate a TON address."""
    try:
        Address(address)
        return True
    except Exception:
        return False

def get_ton_seqno(address: str) -> int:
    """Get the sequence number (seqno) for the sender's wallet."""
    try:
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "runGetMethod",
            "params": {
                "address": address,
                "method": "seqno",
                "stack": []
            }
        }
        response = requests.post(TON_API_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        if 'result' in result and result['result']['stack']:
            seqno = int(result['result']['stack'][0][1], 16)
            return seqno
        raise ValueError("No seqno data in response")
    except Exception as e:
        logger.error(f"Failed to get TON seqno for {address}: {e}")
        raise ValueError(f"Failed to get TON seqno: {e}")

def send_ton(receiver_address: str, amount_ton: float) -> str:
    """Send TON to a recipient address."""
    logger.info(f"Initiating TON transfer: {amount_ton} TON -> {receiver_address}")
    if not validate_ton_address(receiver_address):
        raise ValueError(f"Invalid TON receiver address: {receiver_address}")
    sender_balance = check_ton_balance(TON_SENDER_ADDRESS)
    total_ton = amount_ton + 0.01  # Add 0.01 TON as a fee buffer
    if sender_balance < total_ton:
        raise ValueError(f"Insufficient balance: {sender_balance} TON, need {total_ton} TON")
    try:
        seqno = get_ton_seqno(TON_SENDER_ADDRESS)
        destination = Address(receiver_address)
        amount = to_nano(amount_ton, 'ton')
        transfer = TON_SENDER_WALLET.create_transfer_message(
            to_addr=destination,
            amount=amount,
            seqno=seqno,
            payload=None
        )
        message_boc = transfer["message"].to_boc(False).hex()
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "sendBoc",
            "params": {"boc": message_boc}
        }
        response = requests.post(TON_API_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        if 'result' in result:
            tx_hash = result['result']['transaction_id']['hash']
            logger.info(f"TON transaction successful: {tx_hash}")
            return tx_hash
        raise ValueError("Transaction failed: no result in response")
    except Exception as e:
        logger.error(f"TON transaction failed: {e}\n{traceback.format_exc()}")
        raise ValueError(f"TON transaction failed: {e}")

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

# Price and exchange rate functions (unchanged)
def get_crypto_price(coingecko_id, network="Ethereum"):
    crypto_price_key = f"crypto_price_{coingecko_id}_{network.lower()}"
    crypto_price = cache.get(crypto_price_key)
    if crypto_price is None:
        crypto_price_url = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd"
        logger.info(f"Fetching crypto price for {network} from: {crypto_price_url}")
        try:
            response = requests.get(crypto_price_url, timeout=5)
            response.raise_for_status()
            crypto_price_data = response.json()
            if coingecko_id not in crypto_price_data or "usd" not in crypto_price_data[coingecko_id]:
                raise ValueError(f"No valid price data for {coingecko_id} on {network}")
            crypto_price = Decimal(str(crypto_price_data[coingecko_id]["usd"]))
            cache.set(crypto_price_key, crypto_price, timeout=300)
            logger.info(f"Cached crypto price for {coingecko_id} on {network}: {crypto_price}")
        except requests.RequestException as e:
            logger.error(f"API request failed for {coingecko_id} on {network}: {str(e)}\n{traceback.format_exc()}")
            crypto_price = Decimal("500")
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Data parsing error for {coingecko_id} on {network}: {str(e)}\n{traceback.format_exc()}")
            crypto_price = Decimal("500")
    else:
        logger.info(f"Using cached crypto price for {coingecko_id} on {network}: {crypto_price}")
    return crypto_price

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
            cache.set(exchange_rate_key, base_exchange_rate, timeout=300)
            logger.info(f"Cached exchange rate: {base_exchange_rate}")
        except (requests.RequestException, KeyError, ValueError) as e:
            logger.error(f"Failed to fetch exchange rate: {str(e)}\n{traceback.format_exc()}")
            base_exchange_rate = Decimal("1500")
    else:
        logger.info(f"Using cached exchange rate: {base_exchange_rate}")
    try:
        from .models import ExchangeRateMargin
        margin = ExchangeRateMargin.objects.get(currency_pair="USDT/NGN").profit_margin
    except ExchangeRateMargin.DoesNotExist:
        margin = Decimal("0")
    return base_exchange_rate + margin