from .coinone import CoinoneAPIWrapper
from .upbit import UpbitAPI


def get_api_wrapper(provider, api_key=None, secret_key=None):
    if provider.lower() == 'coinone':
        return CoinoneAPIWrapper(api_key, secret_key)
