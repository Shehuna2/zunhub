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
