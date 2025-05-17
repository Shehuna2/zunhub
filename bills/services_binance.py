import requests
from decimal import Decimal
from django.conf import settings
from binance.client import Client

# Binance API credentials from settings
BINANCE_API_KEY = settings.BINANCE_API_KEY
BINANCE_API_SECRET = settings.BINANCE_API_SECRET

# Profit margin when buying from user (e.g., platform buys at a discount)
# Set in settings.py: SELL_PROFIT_MARGIN = Decimal('0.02')
SELL_MARGIN = getattr(settings, 'SELL_PROFIT_MARGIN', Decimal('0.02'))


def get_binance_client():
    from binance.client import Client
    return Client(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET)


def lookup_rate_binance(asset: str) -> Decimal:
    """
    Fetch the NGN rate for `asset` via CoinGecko and apply the SELL_MARGIN discount.
    """
    # Map asset to CoinGecko IDs
    id_map = {
        'usdt': 'tether',
        'bnb': 'binancecoin',
    }
    cg_id = id_map.get(asset.lower())
    if not cg_id:
        raise ValueError(f"Unsupported asset: {asset}")

    # Query CoinGecko for NGN price
    url = 'https://api.coingecko.com/api/v3/simple/price'
    params = {'ids': cg_id, 'vs_currencies': 'ngn'}
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    market_rate = Decimal(str(data[cg_id]['ngn']))
    # Apply discount margin: buy at (1 - SELL_MARGIN) of market rate
    discounted_rate = (market_rate * (Decimal('1') - SELL_MARGIN)).quantize(Decimal('0.01'))
    return discounted_rate


def verify_transfer_binance(order) -> bool:
    """
    Verify if `order.amount_asset` has been deposited to our Binance account.
    Checks deposit history for matching address and sufficient amount.
    """
    asset_symbol = order.asset.upper()
    deposit_history = get_binance_client.get_deposit_history(asset=asset_symbol)
    target_address = order.details.get('address')

    for entry in deposit_history.get('depositList', []):
        if entry.get('address') == target_address:
            amount_received = Decimal(entry.get('amount', '0'))
            status = entry.get('status')  # 1 = success on Binance
            if amount_received >= order.amount_asset and status == 1:
                return True
    return False
