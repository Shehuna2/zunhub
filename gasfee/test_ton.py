import os
from tonsdk.contract.wallet import Wallets, WalletVersionEnum
from dotenv import load_dotenv

load_dotenv()
SENDER_SEED = os.getenv("TON_SEED_PHRASE")

# Test multiple versions
versions = [WalletVersionEnum.v3r2, WalletVersionEnum.v4r2, WalletVersionEnum.w5]
for version in versions:
    _, _, _, wallet = Wallets.from_mnemonics(SENDER_SEED.split(), version, workchain=0)
    addr_bounce = wallet.address.to_string(True, True, True)   # Bounceable (EQ)
    addr_nonbounce = wallet.address.to_string(True, False, True)  # Non-bounceable (UQ)
    print(f"{version}: Bounceable: {addr_bounce}")
    print(f"{version}: Non-bounceable: {addr_nonbounce}")
    print(f"Public Key: {wallet.public_key.hex()}\n")