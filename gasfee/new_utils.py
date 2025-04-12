import base58
import binascii
import os
import logging
from dotenv import load_dotenv

# Sui-specific imports
from pysui.sui.sui_clients.sync_client import SuiClient
from pysui.sui.sui_clients.common import SuiRpcResult
from pysui.sui.sui_txn import SyncTransaction
from solders.keypair import Keypair as SuiKeypair  # pysui uses solders for keypairs
from solders.pubkey import Pubkey
import traceback
import sys


logger = logging.getLogger(__name__)

load_dotenv()  # Load environment variables from .env file

# Validate essential environment variables
def get_env_var(var_name, required=True):
    value = os.getenv(var_name)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {var_name}")
    return value


# Sui setup
SUI_RPC_URL = get_env_var("SUI_RPC_URL", required=True)
SUI_PRIVATE_KEY = get_env_var("SUI_PRIVATE_KEY", required=True).strip('"')

private_key_str = SUI_PRIVATE_KEY.replace("suiprivkey", "")

# Define a simple config class
class SimpleSuiConfig:
    def __init__(self, rpc_url):
        self.rpc_url = rpc_url

# Initialize SuiClient
sui_config = SimpleSuiConfig(SUI_RPC_URL)
sui_client = SuiClient(config=sui_config)


try:
    # Decode as hex
    private_key_bytes = binascii.unhexlify(private_key_str)
    SUI_SENDER_KEYPAIR = SuiKeypair.from_bytes(private_key_bytes)
    SUI_SENDER_ADDRESS = str(SUI_SENDER_KEYPAIR.pubkey())
    print(f"Sender Address: {SUI_SENDER_ADDRESS}")
except binascii.Error as e:
    logger.error(f"Hex decoding failed: {e}")
    raise ValueError(f"Invalid SUI_PRIVATE_KEY format: {e}")
except Exception as e:
    logger.error(f"Failed to create SuiKeypair: {e}")
    raise ValueError(f"Failed to create SuiKeypair: {e}")


def check_sui_balance(address: str) -> float:
    """Check the SUI balance of an address."""
    try:
        result = sui_client.get_total_balance(address=address)
        if result.is_success():
            # Sum all coin balances (in MIST, 1 SUI = 10^9 MIST)
            total_balance_mist = sum(
                int(coin["total_balance"]) for coin in result.result_data["SUI"]
            )
            balance_sui = total_balance_mist / 1_000_000_000  # Convert MIST to SUI
            logger.info(f"Balance for {address}: {balance_sui} SUI")
            return balance_sui
        raise ValueError(f"Failed to fetch balance: {result.result_string}")
    except Exception as e:
        logger.error(f"Failed to fetch SUI balance for {address}: {e}")
        raise ValueError(f"Failed to fetch SUI balance: {e}")

def validate_sui_address(address: str) -> bool:
    """Validate a Sui address."""
    try:
        # Sui addresses are hex strings starting with '0x' and 64 characters long (32 bytes)
        if not address.startswith("0x") or len(address) != 66:  # 2 for '0x' + 64 hex chars
            return False
        # Attempt to create a Pubkey (basic validation)
        Pubkey.from_string(address[2:])  # Remove '0x' prefix
        return True
    except Exception:
        return False

def estimate_sui_gas_fee() -> float:
    """Estimate the gas fee for a Sui transfer transaction."""
    # For simplicity, use a fixed estimate; ideally, simulate the transaction
    return 0.001  # 0.001 SUI as a reasonable default

def send_sui(receiver_address: str, amount_sui: float) -> str:
    """Send SUI to the receiver address and return the transaction digest."""
    logger.info(f"Initiating SUI transfer: {amount_sui} SUI -> {receiver_address}")
    if not validate_sui_address(receiver_address):
        raise ValueError(f"Invalid Sui receiver address: {receiver_address}")

    sender_balance = check_sui_balance(SUI_SENDER_ADDRESS)
    gas_fee = estimate_sui_gas_fee()
    total_sui_needed = amount_sui + gas_fee

    if sender_balance < total_sui_needed:
        raise ValueError(f"Insufficient SUI balance: {sender_balance} SUI, need {total_sui_needed} SUI")

    try:
        # Build transaction using SyncTransaction
        txn = SyncTransaction(client=sui_client, initial_sender=SUI_SENDER_KEYPAIR)
        # Convert amount to MIST (1 SUI = 10^9 MIST)
        amount_mist = int(amount_sui * 1_000_000_000)
        gas_budget_mist = int(gas_fee * 1_000_000_000)  # Gas budget in MIST
        txn.transfer_sui(to_address=receiver_address, amount=amount_mist)
        
        # Execute transaction
        result = txn.execute(gas_budget=gas_budget_mist)
        if result.is_success():
            tx_digest = result.result_data.digest
            logger.info(f"Sui transaction successful: {tx_digest}")
            return tx_digest
        else:
            raise ValueError(f"Transaction failed: {result.result_string}")
    except Exception as e:
        logger.error(f"Sui transaction failed: {e}\n{traceback.format_exc()}")
        raise ValueError(f"Sui transaction failed: {e}")