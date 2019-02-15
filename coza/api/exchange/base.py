import requests
from abc import ABC, abstractmethod
from .exception import ExchangeAPIException


def private_api(func):
	def check_keys(self, *args, **kwargs):
		assert (self.api_key and self.secret_key), "This API requires valid api_key and secret_key"
		return func(self, *args, **kwargs)
	return check_keys


class BaseAPIWrapper(ABC):
	def __init__(self, exchange, api_key=None, secret_key=None):
		self.exchange = exchange
		self.api_key = api_key
		self.secret_key = secret_key

	def request(self, method, endpoint, **kwargs):
		req = self.prepare_request(method, endpoint, **kwargs)
		resp = session = requests.Session().send(req)

		if resp.status_code == 405:
			raise ExchangeAPIException(self.exchange, req, resp, resp.status_code, 'Coinone Server Error')
		elif resp.status_code >= 500:
			raise ExchangeAPIException(self.exchange, req, resp, resp.status_code, 'Internal Server Error')
		else:
			return resp

	@abstractmethod
	def prepare_request(self, method, endpoint, **kwargs):
		raise NotImplementedError

	@abstractmethod
	def is_req_succeed(self, resp):
		raise NotImplementedError

	@abstractmethod
	def get_error_message(self, resp):
		raise NotImplementedError


	@abstractmethod
	def get_transactions(self, currency, *args, **kwargs):
		raise NotImplementedError

	@abstractmethod
	def get_ticker(self, currency, *args, **kwargs):
		raise NotImplementedError

	@abstractmethod
	def get_orderbook(self, currency, fiat, limit, *args, **kwargs):
		raise NotImplementedError

	@abstractmethod
	def validate_api_key(self):
		raise NotImplementedError

	@abstractmethod
	def get_balance(self):
		raise NotImplementedError

	@abstractmethod
	def order_buy(self, currency, fiat, price, quantity):
		raise NotImplementedError

	@abstractmethod
	def order_sell(self, currency, fiat, price, quantity):
		raise NotImplementedError

	@abstractmethod
	def order_list(self, currency):
		raise NotImplementedError

	@abstractmethod
	def order_cancel(self, order_type, order_id, currency, fiat, price, quantity):
		raise NotImplementedError

	@abstractmethod
	def order_status(self, order_id):
		raise NotImplementedError