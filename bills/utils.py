import logging
import uuid
import requests
from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

VTPASS_URL = settings.VTPASS_SANDBOX_URL
API_KEY = settings.VTPASS_API_KEY
SECRET_KEY = settings.VTPASS_SECRET_KEY

SERVICE_ID_MAP = {
    "mtn": "mtn",
    "glo": "glo",
    "airtel": "airtel",
    "9mobile": "etisalat",
}

def _extract_txid(data: dict) -> str | None:
    content = data.get("content", {}) or {}
    txid = content.get("transactionId")
    if txid:
        return txid
    return content.get("transactions", {}).get("transactionId")

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def _make_api_call(url, payload, headers):
    return requests.post(url, json=payload, headers=headers, timeout=10)

def purchase_airtime(phone: str, amount: float, network: str) -> dict:
    request_id = str(uuid.uuid4())
    service_id = SERVICE_ID_MAP.get(network)
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
        resp = _make_api_call(VTPASS_URL, payload, headers)
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
    service_id = SERVICE_ID_MAP.get(network)
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
        "amount": amount,
        "phone": phone,
        "variation_code": variation_code,
    }

    try:
        resp = _make_api_call(VTPASS_URL, payload, headers)
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