import base64
import ed25519
import json
import requests
import os

def load_sui_sender_keypair():
    """
    Load the SUI sender private key from an environment variable.
    The key should be stored as a Base64 string.
    """
    SUI_SENDER_PRIVATE_KEY_B64 = os.getenv("SUI_SENDER_PRIVATE_KEY")
    if not SUI_SENDER_PRIVATE_KEY_B64:
        raise ValueError("Missing SUI_SENDER_PRIVATE_KEY in environment")
    private_key_bytes = base64.b64decode(SUI_SENDER_PRIVATE_KEY_B64)
    signing_key = ed25519.SigningKey(private_key_bytes)
    verifying_key = signing_key.get_verifying_key()
    # (Optional) You might compute the Sui address here from the public key.
    return signing_key, verifying_key


def validate_sui_address(address: str) -> bool:
    """
    Basic validation for Sui addresses. Sui addresses are usually represented as a hex string starting with "0x".
    They can be either 42 or 66 characters long.
    """
    if address.startswith("0x") and len(address) in (42, 66):
        try:
            int(address[2:], 16)
            return True
        except ValueError:
            return False
    return False



def get_sui_gas_object(sui_sender_address: str, sui_rpc_url: str) -> str:
    """
    Retrieve the first coin object from the Sui sender account to be used as the gas coin.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "sui_getCoins",
        "params": [sui_sender_address, {"limit": 1}]
    }
    response = requests.post(sui_rpc_url, json=payload)
    response.raise_for_status()
    result = response.json().get("result")
    if result and result.get("data"):
        # Return the object ID of the first coin for gas payment
        return result["data"][0]["coinObjectId"]
    else:
        raise ValueError("No coin available for gas payment in the SUI sender account.")

def send_sui(receiver_address: str, amount: float) -> str:
    """
    Construct and send a SUI transfer transaction using Sui RPC.
    
    Note:
    - This simplified example assumes:
      - You have a SUI_SENDER_ADDRESS and SUI_SENDER_PRIVATE_KEY (Base64 encoded) in your env.
      - The SUI RPC URL is defined in the environment (or you can use a default testnet/mainnet URL).
      - SUI tokens use 9 decimals.
    - A production-grade implementation would require transaction signing with the sender’s private key.
    """
    import os
    import base64
    import ed25519

    SUI_RPC_URL = os.getenv("SUI_RPC_URL", "https://fullnode.mainnet.sui.io:443")
    SUI_SENDER_ADDRESS = os.getenv("SUI_SENDER_ADDRESS")
    SUI_SENDER_PRIVATE_KEY_B64 = os.getenv("SUI_SENDER_PRIVATE_KEY")
    
    if not (SUI_SENDER_ADDRESS and SUI_SENDER_PRIVATE_KEY_B64):
        raise ValueError("Missing SUI sender configuration (address or private key).")

    # (In a complete implementation you would sign the transaction payload with your private key.)
    # For this example, we assume that the RPC node accepts an unsigned transaction or that
    # signing is handled externally (or via a Sui SDK).
    # ---
    # For demonstration, we retrieve a gas coin object:
    gas_object_id = get_sui_gas_object(SUI_SENDER_ADDRESS, SUI_RPC_URL)
    
    # Prepare the parameters for the sui_transferSui RPC call.
    # We assume SUI uses 9 decimals (so we multiply by 10**9).
    tx_params = [
        SUI_SENDER_ADDRESS,               # sender
        receiver_address,                 # recipient
        int(amount * 10**9),              # amount in smallest unit
        1000,                             # gas budget (example value)
        gas_object_id,                    # gas coin object ID
        1                                 # gas price (example value)
    ]
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "sui_transferSui",
        "params": tx_params
    }
    
    response = requests.post(SUI_RPC_URL, json=payload)
    response.raise_for_status()
    result = response.json()
    
    if "result" in result:
        tx_digest = result["result"]
        return tx_digest
    else:
        raise ValueError(f"SUI transaction failed: {result}")
