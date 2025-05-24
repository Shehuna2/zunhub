# p2p/services.py
from decimal import Decimal
from django.conf import settings

# import specific source integrations
from .services_binance import lookup_rate_binance, verify_transfer_binance
# Future integrations: from .services_bybit import ...

# CoinGecko fallback
import requests

def lookup_rate(asset: str, source: str) -> Decimal:
    """
    Dispatch to source-specific rate lookup. If unsupported, fallback to CoinGecko with SELL_MARGIN.
    """
    if source == 'binance':
        return lookup_rate_binance(asset)
    # elif source == 'bybit':
    #     return lookup_rate_bybit(asset)
    # ... other exchange-specific calls
    
    # Generic fallback via CoinGecko
    id_map = {'usdt': 'tether', 'bnb': 'binancecoin'}
    cg_id = id_map.get(asset.lower())
    if not cg_id:
        raise ValueError(f"Unsupported asset: {asset}")

    url = 'https://api.coingecko.com/api/v3/simple/price'
    params = {'ids': cg_id, 'vs_currencies': 'ngn'}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    rate_ngn = Decimal(str(data[cg_id]['ngn']))

    # apply SELL_MARGIN if defined
    sell_margin = getattr(settings, 'SELL_PROFIT_MARGIN', Decimal('0.02'))
    discounted = (rate_ngn * (Decimal('1.0') - sell_margin)).quantize(Decimal('0.01'))
    return discounted


def get_receiving_details(source: str, asset: str) -> dict:
    """
    Return platform's receiving details for each source.
    """
    # could also delegate per source if formats differ
    if source == 'binance':
        # return details from settings or DB
        return settings.BINANCE_RECEIVE_DETAILS  # e.g. {'uid':'...', 'email':'...'}
    elif source == 'bybit':
        return settings.BYBIT_RECEIVE_DETAILS
    elif source == 'bitget':
        return settings.BITGET_RECEIVE_DETAILS
    elif source == 'mexc':
        return settings.MEXC_RECEIVE_DETAILS
    elif source == 'gateio':
        return settings.GATEIO_RECEIVE_DETAILS
    
    if source == 'wallet':
        return {'address': settings.PLATFORM_WALLET_ADDRESS}

    raise ValueError(f"Unsupported source: {source}")


def verify_transfer(order) -> bool:
    """
    Dispatch to source-specific verification.
    """
    source = order.source.lower()
    if source == 'binance':
        return verify_transfer_binance(order)
    # elif source == 'bybit':
    #     return verify_transfer_bybit(order)
    # ... other exchange-specific
    
    # # generic on-chain
    # from .services_blockchain import verify_transfer_blockchain
    # return verify_transfer_blockchain(order)












# # p2p/services.py

# from decimal import Decimal

# def lookup_rate(asset: str, source: str) -> Decimal:
#     """
#     Return the current NGN rate for `asset` on `source` exchange.
#     E.g. call Binance/Bybit API or your own caching layer.
#     """
#     # TODO: Replace with real logic
#     if asset == 'usdt':
#         return Decimal('1000.00')   # example: ₦1,000 per USDT
#     if asset == 'bnb':
#         return Decimal('180000.00') # example: ₦180,000 per BNB
#     return Decimal('0')

# def get_receiving_details(source: str, asset: str) -> dict:
#     """
#     Return a dict of how the user should send funds to your platform.
#     E.g. for Binance: {'uid': '1234', 'email': 'you@platform.com'}
#          for wallet:  {'address': '0xABCDEF...'}
#     """
#     details = {}
#     if source == 'binance':
#         details = {'uid': '987654', 'email': 'deposits@platform.com'}
#     elif source == 'wallet':
#         details = {'address': '0xYourPlatformWalletAddress'}
#     # … add others …
#     return details



# def verify_transfer(order) -> bool:
#     """
#     Check via exchange API or blockchain if the user has sent `order.amount_asset`
#     of `order.asset` to our receiving address/account in `order.details`.
#     Returns True if verified, False otherwise.
#     """
#     # TODO: Implement real verification logic:
#     #  - For exchanges: call their deposit-history endpoint and match tx
#     #  - For on-chain: use Web3 to check for incoming tx to `order.details['address']`
#     return True
