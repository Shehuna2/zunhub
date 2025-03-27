import os
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

# ✅ Validate essential environment variables
def get_env_var(var_name, required=True):
    value = os.getenv(var_name)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {var_name}")
    return value

# ✅ TON Setup using tonsdk.py
TON_API_URL = get_env_var("TON_API_URL")
ton_client = ToncenterClient(base_url=TON_API_URL, api_key=get_env_var("TONCENTER_API_KEY"))
SENDER_SEED = get_env_var("TON_SEED_PHRASE")

_, _, _, wallet = Wallets.from_mnemonics(SENDER_SEED.split(), WalletVersionEnum.v3r2, workchain=0)
SENDER_ADDRESS = wallet.address.to_string(True, True, True)


print(type(wallet), wallet)  # Debugging line
