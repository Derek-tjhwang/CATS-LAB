import requests
import hmac
import hashlib
import json
import base64
import time
import math
from fake_useragent import UserAgent

from .base import BaseAPIWrapper, private_api
from .exception import ExchangeAPIException

def truncate(f, n):
	return math.floor(round(f * 10 ** n, n)) / 10 ** n

	

class CoinoneAPIWrapper(BaseAPIWrapper):
	host = 'https://api.coinone.co.kr/'
	error_messages = {
		'4': 'Blocked user access',
		'11': 'Access token is missing',
		'12': 'Invalid access token',
		'40': 'Invalid API permission',
		'50': 'Authenticate error',
		'51': 'Invalid API',
		'52': 'Deprecated API',
		'53': 'Two Factor Auth Fail',
		'100': 'Session expired',
		'101': 'Invalid format',
		'102': 'ID is not exist',
		'103': 'Lack of Balance',
		'104': 'Order id is not exist',
		'105': 'Price is not correct',
		'106': 'Locking error',
		'107': 'Parameter error',
		'111': 'Order id is not exist',
		'112': 'Cancel failed',
		'113': 'Quantity is too low(ETH, ETC > 0.01)',
		'120': 'V2 API payload is missing',
		'121': 'V2 API signature is missing',
		'122': 'V2 API nonce is missing',
		'123': 'V2 API signature is not correct',
		'130': 'V2 API Nonce value must be a positive integer',
		'131': 'V2 API Nonce is must be bigger then last nonce',
		'132': 'V2 API body is corrupted',
		'141': 'Too many limit orders',
		'150': "It's V1 API. V2 Access token is not acceptable",
		'151': "It's V2 API. V1 Access token is not acceptable",
		'200': 'Wallet Error',
		'202': 'Limitation error',
		'210': 'Limitation error',
		'220': 'Limitation error',
		'221': 'Limitation error',
		'310': 'Mobile auth error',
		'311': 'Need mobile auth',
		'312': 'Name is not correct',
		'330': 'Phone number error',
		'404': 'Page not found error',
		'405': 'Server error',
		'429': 'Too Many Requests',
		'444': 'Locking error',
		'500': 'Email error',
		'501': 'Email error',
		'777': 'Mobile auth error',
		'778': 'Phone number error',
		'779': 'Address error',
		'1202': 'App not found',
		'1203': 'Already registered',
		'1204': 'Invalid access',
		'1205': 'API Key error',
		'1206': 'User not found',
		'1207': 'User not found',
		'1208': 'User not found',
		'1209': 'User not found'
	}

	def __init__(self, api_key=None, secret_key=None):
		super().__init__('coinone', api_key, secret_key)
		# self.ticker_keys = ['high', 'low', 'last', 'first', 'volume',
		# 					'yesterday_high', 'yesterday_low', 'yesterday_last', 'yesterday_first', 'yesterday_volume']

	def get_base_payload(self):
		return {
			'access_token': self.api_key
		}

	@staticmethod
	def get_encoded_payload(payload):
		payload['nonce'] = int(time.time()*1000)
		dumped_json = json.dumps(payload)
		encoded_json = base64.b64encode(dumped_json.encode())
		return encoded_json

	def get_signature(self, encoded_payload):
		signature = hmac.new(self.secret_key.upper().encode(), encoded_payload, hashlib.sha512)
		return signature.hexdigest()

	def prepare_request(self, method, endpoint, **kwargs):
		params = dict(**kwargs.get('additional_params', {}))
		payload = dict(**kwargs.get('additional_payload', {}))
		useragent = UserAgent()
		headers = {
			'Content-Type': 'application/json'
		}
		if kwargs.get('private', True):
			payload = self.get_encoded_payload(dict(payload, **self.get_base_payload()))
			signature = self.get_signature(payload)
			headers = dict(headers, **{
				'X-COINONE-PAYLOAD': payload,
				'X-COINONE-SIGNATURE': signature,
				'User-Agent':useragent.random
			})

		return requests.Request(
			method=method,
			url=(self.host + endpoint),
			headers=headers,
			params=params,
			data=payload
		).prepare()

	def is_req_succeed(self, resp):
		try:
			data = resp.json()
			return int(data.get('errorCode')) == 0
		except Exception as e:
			return json.loads(resp.content.decode('utf-8').replace('“','"').replace('”','"')).get("errorCode") == 0

	def get_error_message(self, resp):
		try:
			data = resp.json()
			return self.error_messages.get(str(data.get('errorCode')))
		except Exception as e:
			return self.error_messages.get(json.loads(resp.content.decode('utf-8').replace('“','"').replace('”','"')).get("errorCode"))

	def get_ticker(self, currency, *args, **kwargs):
		endpoint = 'ticker/'
		resp = self.request('GET', endpoint, additional_params={
			'currency': currency
		}, private=False)
		if not self.is_req_succeed(resp):
			return self.get_error_message(resp)
		else:
			resp = resp.json()
		return {k: resp[k] for k in resp.keys() & self.ticker_keys}

	def get_transactions(self, currency, *args, **kwargs):
		endpoint = 'trades/'
		resp = self.request('GET', endpoint, additional_params={
			'currency': currency,
			'period': kwargs.get('period', 'hour')
		}, private=False)
		if not self.is_req_succeed(resp):
			return self.get_error_message(resp)
		else:
			resp = resp.json()
		return resp.get('completeOrders')

	def get_orderbook(self, currency, fiat, limit, *args, **kwargs):
		endpoint = 'orderbook/'
		resp = self.request('GET', endpoint, additional_params={
			'currency': currency
		}, private=False)
		if not self.is_req_succeed(resp):
			return self.get_error_message(resp)
		else:
			resp = resp.json()
		return {
			'bids': [(lambda x: {'price': int(x['price']), 'quantity': float(x['qty'])})(x) for x in resp.get('bid')][:limit],
			'asks': [(lambda x: {'price': int(x['price']), 'quantity': float(x['qty'])})(x) for x in resp.get('ask')][:limit]
		}

	@private_api
	def validate_api_key(self):
		endpoint = 'v2/account/user_info/'
		try:
			resp = self.request('POST', endpoint)
			if not self.is_req_succeed(resp):
				return self.get_error_message(resp)
			else:
				resp = resp.json()
			return int(resp['errorCode']) == 0
		except:
			return False

	@private_api
	def get_balance(self):
		endpoint = 'v2/account/balance/'
		resp = self.request('POST', endpoint)
		if not self.is_req_succeed(resp):
			return self.get_error_message(resp)
		else:
			balance = resp.json()
		data = {}
		for key, val in balance.items():
			if key in ['result', 'errorCode', 'normalWallets']:
				continue

			data[f'{key.lower()}_krw' if key != 'krw' else 'krw'] = {
				'avail': float(val['avail']),
				'balance': float(val['balance'])
			}

		return data

	@private_api
	def order_buy(self, currency, fiat, price, quantity):
		price = int(price)
		quantity = truncate(quantity, 4)
		endpoint = 'v2/order/limit_buy/'
		try:
			resp = self.request('POST', endpoint, additional_payload={
				'currency': currency,
				'price': price,
				'qty': quantity
			})
			if not self.is_req_succeed(resp):
				return dict(result=False, msg=self.get_error_message(resp))
			else:
				resp = resp.json()
			return dict(result=True, order_id=resp.get('orderId'))
		except ExchangeAPIException as e:
			e.detail += f'\n주문상세: BUY {price}{fiat.upper()} x {quantity}{currency.upper()}'
			raise e

	@private_api
	def order_sell(self, currency, fiat, price, quantity):
		price = int(price)
		quantity = truncate(quantity, 4)
		endpoint = 'v2/order/limit_sell/'
		try:
			resp = self.request('POST', endpoint, additional_payload={
				'currency': currency,
				'price': price,
				'qty': quantity
			})
			if not self.is_req_succeed(resp):
				return dict(resul=False, msg=self.get_error_message(resp))
			else:
				resp = resp.json()
			return dict(result=True, order_id=resp.get('orderId'))
		except ExchangeAPIException as e:
			e.detail += f'\n주문상세: SELL {price}{fiat.upper()} x {quantity}{currency.upper()}'
			raise e

	@private_api
	def order_list(self, currency):
		endpoint = 'v2/order/limit_orders/'
		try:
			resp = self.request('POST', endpoint, additional_payload={
				'currency': currency
			})
			if not self.is_req_succeed(resp):
				return self.get_error_message(resp)
			else:
				resp = resp.json()
			return dict(order_list=resp.get('limitOrders'))
		except ExchangeAPIException as e:
			e.detail += f'\n주문목록 조회'
			raise e

	@private_api
	def order_cancel(self, order_type, order_id, currency, fiat, price, quantity):
		price = int(price)
		quantity = truncate(quantity, 4)
		endpoint = 'v2/order/cancel/'

		if order_type == "SELL":
			is_ask = 1
		else:
			is_ask = 0

		try:
			resp = self.request('POST', endpoint, additional_payload={
				'order_id': order_id,
				'currency': currency,
				'price': price,
				'qty': quantity,
				'is_ask': is_ask
			})
			if not self.is_req_succeed(resp):
				return self.get_error_message(resp)
			else:
				resp = resp.json()
			return dict(result=resp.get('result'))
		except ExchangeAPIException as e:
			e.detail += f'\n주문상세: CANCEL {price}{fiat.upper()} x {quantity}{currency.upper()}'
			raise e
	
	@private_api
	def order_status(self, currency, order_id):
		endpoint = 'v2/order/order_info/'
		try:
			resp = self.request('POST', endpoint, additional_payload={
				'order_id': order_id,
				'currency': currency
			})
			if not self.is_req_succeed(resp):
				return self.get_error_message(resp)
			else:
				resp = resp.json()
			return dict(status=resp.get('status'), info=resp.get('info'))
		except ExchangeAPIException as e:
			e.detail += f'\n주문현황 조회'
			raise e


	@private_api
	def order_complete(self, currency):
		endpoint = 'v2/order/complete_orders/'
		try:
			resp = self.request('POST', endpoint, additional_payload={
				'currency': currency
			})
			if not self.is_req_succeed(resp):
				return self.get_error_message(resp)
			else:
				resp = resp.json()

			return dict(result=resp.get('result'), info=resp.get('completeOrders'))

		except ExchangeAPIException as e:
			e.detail += f'\n완료주문 조회'
			raise e