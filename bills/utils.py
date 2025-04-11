import logging
import uuid
import requests
from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

VTPASS_URL = settings.VTPASS_SANDBOX_URL  # e.g., "https://sandbox.vtpass.com/api/"
API_KEY = settings.VTPASS_API_KEY
SECRET_KEY = settings.VTPASS_SECRET_KEY

AIRTIME_SERVICE_ID_MAP = {
    "mtn": "mtn",
    "airtel": "airtel",
    "glo": "glo",
    "9mobile": "etisalat",
}

DATA_SERVICE_ID_MAP = {
    "mtn": "mtn-data",
    "airtel": "airtel-data",
    "glo": "glo-data",
    "9mobile": "etisalat-data",
}

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def _make_api_call(url, payload=None, headers=None, method="POST"):
    if method == "POST":
        return requests.post(url, json=payload, headers=headers, timeout=10)
    elif method == "GET":
        return requests.get(url, headers=headers, timeout=10)

def _extract_txid(data: dict) -> str | None:
    content = data.get("content", {}) or {}
    txid = content.get("transactions", {}).get("transactionId")
    return txid

def purchase_airtime(phone: str, amount: float, network: str) -> dict:
    request_id = str(uuid.uuid4())
    service_id = AIRTIME_SERVICE_ID_MAP.get(network, network)  # Fallback to network if not mapped
    if not service_id:
        raise ValueError(f"Unsupported network: {network}")

    logger.info(f"Initiating airtime purchase: ₦{amount} for {phone} on {network} (req_id={request_id})")
    headers = {
        "Content-Type": "application/json",
        "api-key": API_KEY,
        "secret-key": SECRET_KEY,
    }
    payload = {
        "request_id": request_id,
        "serviceID": service_id,
        "amount": amount,
        "phone": phone,
    }

    try:
        resp = _make_api_call(VTPASS_URL + "pay", payload, headers)
        resp.raise_for_status()
        data = resp.json()
        logger.debug(f"VTpass response: {data}")

        if data.get("code") == "000":
            txid = _extract_txid(data)
            logger.info(f"Airtime purchase successful: {txid}")
            return {"success": True, "transaction_id": txid}
        else:
            msg = data.get("response_description", "Unknown error")
            logger.error(f"Airtime purchase failed: {msg}")
            raise ValueError(msg)
    except requests.RequestException as e:
        logger.error(f"VTpass API error: {e}")
        raise ValueError(f"Failed to process airtime purchase: {e}")

def purchase_data(phone: str, amount: float, network: str, variation_code: str) -> dict:
    request_id = str(uuid.uuid4())
    service_id = DATA_SERVICE_ID_MAP.get(network)
    if not service_id:
        raise ValueError(f"Unsupported network: {network}")

    logger.info(f"Initiating data purchase: ₦{amount} for {phone} on {network} ({variation_code}) (req_id={request_id})")
    headers = {
        "Content-Type": "application/json",
        "api-key": API_KEY,
        "secret-key": SECRET_KEY,
    }
    payload = {
        "request_id": request_id,
        "serviceID": service_id,
        "billersCode": phone,
        "variation_code": variation_code,
        "amount": amount,  # Optional per docs, included for clarity
        "phone": phone,
    }

    try:
        resp = _make_api_call(VTPASS_URL + "pay", payload, headers)
        resp.raise_for_status()
        data = resp.json()
        logger.debug(f"VTpass response: {data}")

        if data.get("code") == "000":
            txid = _extract_txid(data)
            logger.info(f"Data purchase successful: {txid}")
            return {"success": True, "transaction_id": txid}
        else:
            msg = data.get("response_description", "Unknown error")
            logger.error(f"Data purchase failed: {msg}")
            raise ValueError(msg)
    except requests.RequestException as e:
        logger.error(f"VTpass API error: {e}")
        raise ValueError(f"Failed to process data purchase: {e}")

def get_data_plans(network: str) -> list:
    """Fetch available data plans for a given network from VTpass."""
    service_id = DATA_SERVICE_ID_MAP.get(network)
    if not service_id:
        raise ValueError(f"Unsupported network: {network}")

    url = f"{VTPASS_URL}service-variations?serviceID={service_id}"
    
    headers = {
        "api-key": API_KEY,
        "secret-key": SECRET_KEY,
    }

    try:
        resp = _make_api_call(url, method="GET", headers=headers)
        resp.raise_for_status()
        data = resp.json()
        logger.debug(f"VTpass data plans response: {data}")

        if data.get("response_description") != "000":
            raise ValueError(data.get("response_description", "Failed to fetch plans"))

        plans = data.get("content", {}).get("variations", [])
        formatted_plans = [
            {
                "variation_code": plan["variation_code"],
                "amount": float(plan["variation_amount"]),
                "description": plan["name"],
            }
            for plan in plans
        ]
        return formatted_plans

    except requests.RequestException as e:
        logger.error(f"Failed to fetch data plans from VTpass: {e}")
        raise ValueError(f"Unable to fetch data plans: {e}")