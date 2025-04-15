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
PRIMARY_TON_URL = "https://toncenter.com/api/v2/jsonRPC"
SECONDARY_TON_URL = "https://tonapi.io/api/v2/jsonRPC"  # Adjust if different
TON_API_KEY = get_env_var("TON_API_KEY", required=True)


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


def make_ton_api_call(payload):
    """Make a TON API call with fallback to secondary endpoint."""
    headers = {"X-API-Key": TON_API_KEY} if TON_API_KEY else {}
    
    # Attempt Primary Endpoint
    try:
        response = requests.post(PRIMARY_TON_URL, json=payload, headers=headers)
        logger.debug(f"[Primary] Request: {json.dumps(payload, indent=2)}")
        logger.debug(f"[Primary] Response: {response.text}")
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        logger.error(f"Primary TON API failed: {e} - Response: {response.text}")
        
        # Attempt Secondary Endpoint
        try:
            response = requests.post(SECONDARY_TON_URL, json=payload, headers=headers)
            logger.debug(f"[Fallback] Request: {json.dumps(payload, indent=2)}")
            logger.debug(f"[Fallback] Response: {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e2:
            logger.error(f"Fallback TON API failed: {e2} - Response: {response.text}")
            raise ValueError(f"Both TON API calls failed: {e2} - Last response: {response.text}")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((requests.exceptions.RequestException, ValueError))
)
def ensure_wallet_active(address: str):
    """Ensure the wallet is active/deployed with retry."""
    if not is_ton_wallet_deployed(address):
        raise ValueError(f"Wallet {address} is not active/deployed")
    logger.info(f"Wallet {address} is active/deployed")

def check_ton_balance(address: str) -> float:
    """Check the TON balance of an address."""
    try:
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "getAddressBalance",
            "params": {"address": address}
        }
        print("Sending TON Payload:", json.dumps(payload, indent=2))
        result = make_ton_api_call(payload)
        if 'result' in result:
            balance = int(result['result']) / 1_000_000_000  # TON uses 9 decimals
            logger.info(f"Balance for {address}: {balance} TON")
            return balance
        raise ValueError("No balance data in response")
    except Exception as e:
        logger.error(f"Failed to fetch TON balance for {address}: {e}")
        raise ValueError(f"Failed to fetch TON balance: {e}")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((requests.exceptions.RequestException, ValueError))
)
def is_ton_wallet_deployed(address: str) -> bool:
    """Check if a TON wallet is deployed by querying its state with retry."""
    try:
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "getAddressInformation",
            "params": {"address": address}
        }
        print("Sending TON Payload:", json.dumps(payload, indent=2))
        result = make_ton_api_call(payload)
        if 'result' in result:
            state = result['result']['state']
            return state == "active"
        return False
    except Exception as e:
        logger.error(f"Failed to check TON wallet state for {address}: {e}")
        return False  # Fallback to assume undeployed on error

def validate_ton_address(address: str) -> bool:
    """Validate a TON address."""
    try:
        Address(address)
        return True
    except Exception:
        return False

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((requests.exceptions.RequestException, ValueError))
)
def get_ton_seqno(address: str) -> int:
    """Get the sequence number (seqno) for the sender's wallet with retry."""
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
        print("Sending TON Payload:", json.dumps(payload, indent=2))
        result = make_ton_api_call(payload)
        if 'result' in result and result['result']['stack']:
            seqno = int(result['result']['stack'][0][1], 16)
            return seqno
        raise ValueError("No seqno data in response")
    except Exception as e:
        logger.error(f"Failed to get TON seqno for {address}: {e}")
        raise


def estimate_ton_fee(sender_address: str) -> float:
    """Estimate the TON transfer fee based on recent transactions."""
    try:
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "getTransactions",
            "params": {
                "address": sender_address,
                "limit": 5  # Look at the last 5 transactions
            }
        }
        result = make_ton_api_call(payload)  # Your existing API call function
        if 'result' in result:
            fees = [int(tx['fee']) / 1_000_000_000 for tx in result['result'] if 'fee' in tx]
            if fees:
                avg_fee = sum(fees) / len(fees)
                return avg_fee * 1.5  # Add a 50% buffer
        return 0.01  # Default to 0.01 TON if no data
    except Exception as e:
        print(f"Fee estimation failed: {e}")
        return 0.01  # Fallback value

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((requests.exceptions.RequestException, ValueError))
)
def send_ton(receiver_address: str, amount_ton: float, order_id: int) -> tuple[str, float]:
    """Send TON to the receiver address with transaction confirmation."""
    logger.info(f"Initiating TON transfer: {amount_ton} TON -> {receiver_address}")
    if not validate_ton_address(receiver_address):
        raise ValueError(f"Invalid TON receiver address: {receiver_address}")

    ensure_wallet_active(TON_SENDER_ADDRESS)
    sender_balance = check_ton_balance(TON_SENDER_ADDRESS)
    deployment_amount = 0.05  # TON deployment cost
    fee_buffer = estimate_ton_fee(TON_SENDER_ADDRESS)
    total_ton = amount_ton + fee_buffer

    is_deployed = is_ton_wallet_deployed(receiver_address)
    if not is_deployed:
        logger.info(f"Recipient wallet {receiver_address} is not deployed. Deploying...")
        total_ton += deployment_amount + fee_buffer

    if sender_balance < total_ton:
        raise ValueError(f"Insufficient balance: {sender_balance} TON, need {total_ton} TON")

    # Get initial seqno before any transaction
    initial_seqno = get_ton_seqno(TON_SENDER_ADDRESS)
    logger.info(f"Current seqno: {initial_seqno}")

    try:
        seqno = initial_seqno

        # Handle wallet deployment if needed
        if not is_deployed:
            destination = Address(receiver_address)
            deploy_amount = to_nano(deployment_amount, 'ton')
            deploy_transfer = TON_SENDER_WALLET.create_transfer_message(
                to_addr=destination,
                amount=deploy_amount,
                seqno=seqno,
                payload=None
            )
            deploy_boc = base64.b64encode(deploy_transfer["message"].to_boc(False)).decode('ascii')
            logger.debug(f"Deployment BoC: {deploy_boc}")
            payload = {
                "id": 1,
                "jsonrpc": "2.0",
                "method": "sendBoc",
                "params": {"boc": deploy_boc}
            }
            print("Sending Deployment TON Payload:", json.dumps(payload, indent=2))
            result = make_ton_api_call(payload)
            if not result.get('ok', False):
                raise ValueError(f"Deployment failed: {result}")
            
            # Wait and confirm deployment
            time.sleep(10)
            while not is_ton_wallet_deployed(receiver_address):
                logger.info("Waiting for wallet deployment...")
                time.sleep(5)
            seqno = get_ton_seqno(TON_SENDER_ADDRESS)  # Refresh seqno after deployment
            logger.info(f"Updated seqno after deployment: {seqno}")

        # Send the actual transfer
        destination = Address(receiver_address)
        amount = to_nano(amount_ton, 'ton')
        transfer = TON_SENDER_WALLET.create_transfer_message(
            to_addr=destination,
            amount=amount,
            seqno=seqno,
            payload=None
        )
        message_boc = base64.b64encode(transfer["message"].to_boc(False)).decode('ascii')
        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "sendBoc",
            "params": {"boc": message_boc}
        }
        result = make_ton_api_call(payload)
        
        # Confirm transaction success by checking seqno
        if result.get('ok', False):
            max_attempts = 5
            for attempt in range(settings.TON_SEQNO_MAX_ATTEMPTS):
                time.sleep(settings.TON_SEQNO_CHECK_INTERVAL)
                new_seqno = get_ton_seqno(TON_SENDER_ADDRESS)
                if new_seqno > seqno:
                    logger.info(f"Transaction confirmed with seqno: {new_seqno}")
                    # Attempt to get the hash, but don’t fail if it’s not found
                    tx_hash = get_transaction_hash(TON_SENDER_ADDRESS, receiver_address, amount_ton)
                    if tx_hash == "pending":
                        from .tasks import update_ton_tx_hash
                        update_ton_tx_hash.delay(order_id, TON_SENDER_ADDRESS, receiver_address, amount_ton)
                    return tx_hash, deployment_amount if not is_deployed else 0
                logger.info(f"Attempt {attempt + 1}/{max_attempts}: seqno still {new_seqno}")
            raise ValueError("Transaction not confirmed: seqno did not increment")
        else:
            raise ValueError(f"Transaction failed: invalid response - {result}")

    except Exception as e:
        logger.error(f"TON transaction failed: {e}\n{traceback.format_exc()}")
        raise ValueError(f"TON transaction failed: {e}")

def get_transaction_hash(sender_address: str, receiver_address: str, amount_ton: float) -> str:
    """Retrieve the transaction hash with retries and fallback."""
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            payload = {
                "id": 1,
                "jsonrpc": "2.0",
                "method": "getTransactions",
                "params": {
                    "address": sender_address,
                    "limit": 20  # Increase limit to catch more transactions
                }
            }
            result = make_ton_api_call(payload)
            if 'result' in result:
                transactions = result['result']
                amount_nano = to_nano(amount_ton, 'ton')
                for tx in transactions:
                    if tx['out_msgs']:
                        for out_msg in tx['out_msgs']:
                            tx_value = int(out_msg['value'])
                            # Allow some tolerance for fees
                            if (out_msg['destination'] == receiver_address and 
                                abs(tx_value - amount_nano) < 10_000_000):  # 0.01 TON tolerance
                                return tx['transaction_id']['hash']
                logger.warning(f"Attempt {attempt + 1}/{max_attempts}: No matching transaction found for {amount_ton} TON to {receiver_address}")
            else:
                logger.warning(f"Attempt {attempt + 1}/{max_attempts}: No transaction data in response")
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}/{max_attempts}: Failed to retrieve transaction hash: {e}")
        
        if attempt < max_attempts - 1:
            time.sleep(5)  # Wait before retrying

    logger.warning(f"Could not retrieve transaction hash after {max_attempts} attempts")
    return "pending"  # Fallback to indicate success without hash

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