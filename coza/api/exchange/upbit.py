import requests
import time
import jwt
import re
import pandas as pd

from collections import defaultdict
from urllib.parse import urlencode
from datetime import datetime


class UpbitAPI:

    host = 'https://api.upbit.com/v1/'

    def __init__(self, api_key=None, secret_key=None):
        self.exchange='upbit'
        self.api_key = api_key
        self.secret_key = secret_key

    def request(self, method, endpoint, **kwargs):
        """

        Args:

        Returns:

        """
        try:
            resp = requests.request(method, self.host + endpoint, **kwargs)

            if resp.status_code < 400:
                return resp
            else:
                print(resp.status_code)
        except Exception as e:
            print(e)

        return resp

    def get_remain_req(self, headers):
        """

        Args:

        Returns:

        """
        remain_req = {}
        try:
            for i in headers['Remaining-Req'].split(';'):
                k, v = i.split('=')
                remain_req[k] = int(v) if re.match('[0-9]+', v) else v
        except KeyError as e:
            return dict(error=e)
        except ValueError as e:
            return dict(error=e)

        return remain_req


    def get_token(self, **kwargs):
        payload = {
            'access_key': self.api_key,
            'nonce': int(time.time() * 1000),
        }
        if kwargs.get('query', False):
            payload['query'] = kwargs.get('query')
        jwt_token = jwt.encode(payload,self.secret_key).decode('utf8')
        authorization_token = f'Bearer {jwt_token}'

        return authorization_token


    def get_balance(self):
        endpoint = 'accounts'
        try:
            resp = self.request(
                method='GET',
                endpoint=endpoint,
                headers= {'Authorization': self.get_token()}
            )
            data = dict()
            for i in resp.json():
                data[i.get('currency')] = i
            data['remain_req'] = self.get_remain_req(resp.headers)
        except Exception as e:
            print(e)

        return data


    # 주문 가능 정보
    def get_order_chance(self, market_id):
        """
        Args:

        Returns:

        """

        endpoint = 'orders/chance?'
        query = urlencode({'market': market_id})
        try:
            resp = self.request(
                method='GET',
                endpoint=endpoint + query,
                headers={'Authorization': self.get_token(query=query)}
            )
            data = resp.json()
            data['remain_req'] = self.get_remain_req(resp.headers)
        except Exception as e:
            print(e)
            data = dict(error=e)

        return data


    # 개별 주문 조회
    def get_order_stat(self, order_id):
        """
        Args:

        Returns:

        """
        query = urlencode({'uuid': order_id})
        endpoint = 'order?'
        try:
            resp = self.request(
                method='GET',
                endpoint=endpoint + query,
                headers={'Authorization': self.get_token(query=query)}
            )
            data = resp.json()
            data['remain_req'] = self.get_remain_req(resp.headers)
        except Exception as e:
            print(e)

        return data


    # 주문 리스트 조회
    def get_order_list(self, market_id, state, page=1, order_by='asc'):
        """
        Args:

        Returns:

        """
        query = urlencode(
            {'market': market_id.upper(),
             'state': state.lower(),
             'page': page,
             'order_by': order_by
             })

        endpoint = 'orders?'
        data = {}
        try:
            resp = self.request(
                method='GET',
                endpoint=endpoint + query,
                headers={'Authorization': self.get_token(query=query)},
            )
            data = dict()
            for i in resp.json():
                data[i.get('uuid')] = i
            data['remain_req'] = self.get_remain_req(resp.headers)
        except Exception as e:
            print(e)

        return data


    # 주문하기
    def get_order(self, market_id, side, volume, price, ord_type='limit'):
        """
        Args:
            market(str) : ('KRW-BTC')
            side(str) : (bid, ask)
            volume(NumberString) :
            price(NumberString) :
            ord_type(str) :
            identifier(str) : 조회용 사용자 지정값

        Returns:

        """
        body = {
            'market': market_id.upper(),
            'side': side.lower(),
            'volume': str(volume),
            'price': str(price),
            'ord_type': ord_type,
        }

        query = urlencode(body)
        endpoint = 'orders'
        try:
            resp = self.request(
                method='POST',
                endpoint=endpoint,
                headers={'Authorization': self.get_token(query=query)},
                json=body)
            data = resp.json()
            data['remain_req'] = self.get_remain_req(resp.headers)
        except Exception as e:
            print(e)

        return data

    # 주문 취소하기
    def get_cancel(self, order_id):
        body = {
            'uuid': str(order_id),
        }

        endpoint = 'order?'
        query = urlencode(body)
        try:
            resp = self.request(
                method='DELETE',
                endpoint=endpoint + query,
                headers={'Authorization': self.get_token(query=query)}
            )
            data = resp.json()
            data['remain_req'] = self.get_remain_req(resp.headers)
        except Exception as e:
            print(e)

        return data


    def get_markets(self):
        endpoint = 'market/all'
        data = {}
        try:
            resp = self.request(method='GET', endpoint=endpoint)
            dump_dict = {
                'KRW': defaultdict(list),
                'BTC': defaultdict(list),
                'ETH': defaultdict(list),
                'USDT': defaultdict(list)
            }
            for i in resp.json():
                for k, v in i.items():
                    dump_dict[i['market'].split('-')[0]][k].append(v)
            for k in dump_dict.keys():
                data[k] = pd.DataFrame(dump_dict[k])
            data['remain_req'] = self.get_remain_req(resp.headers)

        except Exception as e:
            print(e)

        return data


    def get_ticks(self, market_id):
        endpoint = 'trades/ticks'
        query = {'market': market_id.upper()}
        try:
            resp = self.request(method='GET', endpoint=endpoint, params=query)
            data = resp.json()
            data['remain_req'] = self.get_remain_req(resp.headers)
        except Exception as e:
            print(e)

        # Todo
        # Tick Data 처리와 DataFrame으로 변환하여 반환

        return data


    def get_orderbook(self, market_id):
        endpoint = 'orderbook'
        query = {'markets': market_id}
        try:
            resp = self.request(method='GET', endpoint=endpoint, params=query)
            data = dict(*resp.json())
            dump = defaultdict(list)
            for i in data['orderbook_units']:
                for k, v in i.items():
                    dump[k.replace('size', 'quantity')].append(v)

            data = dict(
                orderbook = pd.DataFrame(dump),
                remain_req = self.get_remain_req(resp.headers)
            )
        except Exception as e:
            return dict(error=e)

        return data


    def get_candle(self, currency, fiat, interval, end_date=None, period=200):
        minutes = {1, 3, 5, 10, 15, 30, 60, 240}
        if end_date is not None:
            end_date = end_date.strftime(end_date, '%Y-%m-%dT%H:%m:%S')

        if int(interval) in minutes if interval is not str else None:
            endpoint = 'candles/minutes/' + str(interval)
        elif int(interval) % 1440 == 0 if interval is not str else None:
            endpoint = 'candles/days'
        elif interval == 'w':
            endpoint = 'candles/weeks'
        elif interval == 'm':
            endpoint = 'candles/months'
        else:
            return dict(error=f'Not supported interval {interval}')

        market_id = f'{fiat.upper()}-{currency.upper()}'

        query = {
            'market': market_id,
            'to': "" if end_date is None else end_date,
            'count': period
            }
        try:
            resp = self.request(method='GET', endpoint=endpoint, params=query)
            candle_list = resp.json()
            candle_list.reverse()
            dump_dict = {
                'open': [],
                'close': [],
                'high': [],
                'low': [],
                'volume': [],
                'timestamp': []
            }

            for i in candle_list:
                dump_dict['high'].append(i['high_price'])
                dump_dict['close'].append(i['trade_price'])
                dump_dict['open'].append(i['opening_price'])
                dump_dict['low'].append(i['low_price'])
                dump_dict['volume'].append(i['candle_acc_trade_volume'])
                dump_dict['timestamp'].append(
                    datetime.strptime(i['candle_date_time_kst'][:16], '%Y-%m-%dT%H:%M').timestamp())

            candle_df = pd.DataFrame(dump_dict)


        except Exception as e:
            print(e)

        return candle_df








