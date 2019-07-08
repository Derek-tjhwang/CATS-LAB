import time
import requests
import datetime
import pandas as pd

from coza.config import COZA_HOST
from coza.utils import now
from coza.errors import (CozaRequestException, CozaCurrencyException, CozaExchangeException)


def _request(url, method, **kwargs):
    params = kwargs.get('params', {})
    data = kwargs.get('data', {})
    req = requests.Request(method=method,
                           url=url,
                           params=params,
                           json=data).prepare()
    try_cnt = 0
    while try_cnt != 5:
        try:
            resp = requests.Session().send(req)
            if resp.status_code >= 400:
                raise CozaRequestException(req, resp)
            return resp.json()
        except requests.exceptions.ConnectionError as e:
            print(e)
            msg=e
            try_cnt+=1
            time.sleep(0.5)
            continue

    return dict(result=False, msg=msg)


class CandleApi(object):


    default_candle_periods = {
        1: 10080, # minute (1 week)
        3: 3360, # 1 week
        5: 8640, # 1 month
        15: 2880, # 1 month
        30: 1440, # 1 month
        60: 2160, # 3 months
        120: 1080, # 3 months
        240: 540, # 3 months
        360: 360, # 3 months
        1440: 365, # 1 year
        10080: 48, # 1 year
        40320: 12, # 1 year
    }

    @classmethod
    def get(cls, exchange, currency, fiat, interval, from_date=None, until_date=None):
        url = f'{COZA_HOST}/exchanges/{exchange.lower()}/candles'

        # Todo
        #
        # get_available_interval() 함수 만들기
        #

        # Interval Validation
        assert isinstance(interval, int) and interval in [1, 3, 5, 15, 30, 60, 120, 240, 360, 1440, 10080, 40320]


        # Untildate Validation
        assert until_date is None or isinstance(until_date, datetime.datetime)
        if until_date is None:
            until_date = now(exchange=exchange) - datetime.timedelta(minutes=interval)

        assert from_date is None or isinstance(from_date, datetime.datetime)
        default_from_date = until_date - datetime.timedelta(minutes=(interval * cls.default_candle_periods[interval]))
        if from_date is None:
            from_date = default_from_date

        assert from_date < until_date

        candle_list = _request(url, 'GET', params={
            'currency': currency.upper(),
            'fiat': fiat.upper(),
            'interval': interval,
            'start': from_date.strftime('%Y-%m-%dT%H:%M'),
            'until': until_date.strftime('%Y-%m-%dT%H:%M')
        })
        if len(candle_list) != 0:
            try:
                candle_list.reverse()
            except:
                return candle_list

        return candle_list

    @classmethod
    def get_df(cls, exchange, currency, fiat, interval, from_date=None, until_date=None):
        """Get Candle Dataframe

        Args:
            exchange(str): Cryptocurrency exchange name
            currency(str): Cryptocurrency name
            fiat(str): Fiat Currency name
            interval(int): Period of candle
            from_date(Datetime.Datetime): Year, Month, Day
            until_date(Datetime.Datetime): Year, Momth, Day

        Returns:
            pandas.Dataframe

        """
        candle_list = cls.get(exchange, currency, fiat, interval, from_date, until_date)

        m = {'o': 'open',
             'h': 'high',
             'l': 'low',
             'c': 'close',
             'v': 'volume',
             't': 'timestamp'}

        data = {'close': [],
                'open': [],
                'low': [],
                'high': [],
                'volume': [],
                'timestamp': []}
        try:
            for candle in candle_list:
                for k, v in candle.items():
                    data[m[k]].append(v)
        except:
            return candle_list

        return pd.DataFrame(data).sort_values('timestamp').reset_index(drop=True)


class ExchangeApi(object):

    @classmethod
    def get_exchange_info(cls):
        """Get COZA Service exchange and curreny info

        Args:
            None

        Returns:
            exchange_info(dict)

        """
        url = f'{COZA_HOST}/exchanges'

        exchange_li = _request(url, 'GET')
        exchange_info = {}

        for exchange in exchange_li['results']:
            currency_li = []
            if exchange['name'] not in exchange_info.keys():
                for currency in exchange['currencies']:
                    currency_li.append(currency['label'])
                exchange_info[exchange['name']] = [currency_li, exchange['intervals'], exchange['feerate']]

        return exchange_info

    @classmethod
    def get_ticker(cls, exchange, currency):
        """Get current ticker

        Args:
            exchange(str): Cryptocurrency exchagne name
            currency(str): Cryptocurrency name

        Returns:
            data(dict)

        """
        url = f'{COZA_HOST}/exchanges/{exchange.lower()}/ticker'
        data = _request(url, 'GET', params={'currency': currency.upper()})
        return data

    @classmethod
    def get_orderbook(cls, exchange, currency):
        """Get orderbook current time

        Args:
            exchange(str): Cryptocurrency exchange name
            currency(str): Cryptocurrency name

        Returns:
            data(dict)

        """
        url = f'{COZA_HOST}/exchanges/{exchange.lower()}/orderbook'
        data = _request(url, 'GET', params={'currency': currency.upper()})

        return data

    @classmethod
    def get_markets(cls):
        """Get markets upbit exchange

        Returns:
            data(dict)

        """
        url = f'{COZA_HOST}/exchanges/upbit/market'
        resp = _request(url, 'GET')
        data = {}
        try:
            for k in resp.keys():
                if k == 'remain_req':
                    data[k] = resp[k]
                else:
                    data[k] = pd.DataFrame(resp[k])
        except Exception as e:
            print(e)

        return data


class StrategyApi(object):
    @classmethod
    def get_info(cls, str_id):
        url = f'{COZA_HOST}/strategies/{str_id}'
        data = _request(url, 'GET')
        return data
