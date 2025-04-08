import logging
import traceback
import asyncio
from py_near.account import Account
from .utils import get_env_var

logger = logging.getLogger(__name__)

# NEAR configuration
NEAR_RPC_URL = get_env_var("NEAR_RPC_URL", required=True)  # e.g., "https://rpc.mainnet.near.org"
NEAR_PRIVATE_KEY = get_env_var("NEAR_PRIVATE_KEY", required=True).strip('"')
NEAR_ACCOUNT_ID = get_env_var("NEAR_ACCOUNT_ID", required=True)

# Single event loop for the application
loop = asyncio.get_event_loop()

def run_async(coro):
    """Run an asynchronous coroutine using the application's event loop."""
    try:
        return loop.run_until_complete(coro)
    except RuntimeError as e:
        logger.error(f"Event loop error: {e}")
        raise

def check_near_balance(account_id: str) -> float:
    """Check the NEAR balance of an account."""
    try:
        temp_account = Account(account_id=account_id, rpc_addr=NEAR_RPC_URL)
        run_async(temp_account.startup())
        balance_info = run_async(temp_account.get_balance())
        logger.debug(f"Balance info for {account_id}: {balance_info}")

        # Handle balance as integer (yoctoNEAR)
        balance_yocto = int(balance_info) if isinstance(balance_info, int) else int(balance_info.total)
        balance_near = balance_yocto / 10**24
        logger.info(f"Balance for {account_id}: {balance_near} NEAR")
        return balance_near
    except Exception as e:
        logger.error(f"Failed to fetch balance for {account_id}: {e}")
        raise ValueError(f"Failed to fetch balance: {e}")

def validate_near_account_id(account_id: str) -> bool:
    """Validate a NEAR account ID."""
    if not account_id or len(account_id) < 2 or len(account_id) > 64:
        return False
    if not all(c.isalnum() or c in ['.', '_', '-'] for c in account_id):
        return False
    if not (account_id.endswith(".near") or account_id.endswith(".tg")):
        return False
    return True

def send_near(receiver_account_id: str, amount_near: float) -> str:
    """Send NEAR to the receiver account and return the transaction hash."""
    amount_near = float(amount_near)
    logger.info(f"Initiating transfer: {amount_near} NEAR -> {receiver_account_id}")

    # Validate receiver account ID
    if not validate_near_account_id(receiver_account_id):
        raise ValueError(f"Invalid receiver account ID: {receiver_account_id}")

    # Initialize account
    temp_account = Account(
        account_id=NEAR_ACCOUNT_ID,
        private_key=NEAR_PRIVATE_KEY,
        rpc_addr=NEAR_RPC_URL
    )
    run_async(temp_account.startup())

    # Check sender balance
    sender_balance = check_near_balance(NEAR_ACCOUNT_ID)
    gas_fee_near = 0.0001  # Estimated gas fee (100 TGas)
    total_needed = amount_near + gas_fee_near
    if sender_balance < total_needed:
        raise ValueError(f"Insufficient balance: {sender_balance} NEAR, need {total_needed} NEAR")

    try:
        amount_yocto = int(amount_near * 10**24)
        # Send transaction
        result = run_async(temp_account.send_money(receiver_account_id, amount_yocto))
        tx_hash = result.transaction.hash
        logger.info(f"Transaction successful: {tx_hash}")
        return tx_hash
    except Exception as e:
        logger.error(f"Transaction failed: {e}\n{traceback.format_exc()}")
        raise ValueError(f"Transaction failed: {e}")