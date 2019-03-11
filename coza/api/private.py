import json
import time
import base64
import requests

from coza.config import COZA_SECRET, COZA_HOST
from coza.errors import CozaRequestException, CozaNotAuthenticatedException
from coza.logger import logger
from coza.objects import Order
from .exchange import get_api_wrapper

def _make_auth_header(user_uuid):
	return {
		'COZA-SECRET-AUTH': base64.b64encode(json.dumps({
			'user_uuid': user_uuid,
			'secret': COZA_SECRET
		}).encode())
	}


def _request(url, method, user_uuid, **kwargs):
	params = kwargs.get('params', {})
	data = kwargs.get('data', {})
	req = requests.Request(method=method,
						   url=url,
						   headers=_make_auth_header(user_uuid),
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
			msg=e
			try_cnt+=1
			time.sleep(0.5)
			continue

	return dict(result=False, msg=msg)


class TradeApi(object):
	@classmethod
	def initialize(cls, user_uuid, bot_id):
		cls.user_uuid = user_uuid
		cls.bot_id = bot_id

	# 하나의 봇에서 여러 거래소를 사용하는 경우 아래의 accounts 추가 및 order로 변경
	#
	# @classmethod
	# def balance(cls, account: Account):
	# 	url = f'{COZA_HOST}/users/{cls.user_uuid}/excAcnts/{account.uuid}/balance'
	# 	balance = _request(url, 'GET', cls.user_uuid)
	# 	return balance
	#
	# @classmethod
	# def accounts(cls):
	# 	url = f'{COZA_HOST}/users/{cls.user_uuid}/excAcnts'
	# 	accounts = _request(url, 'GET', cls.user_uuid)
	# 	return [Account(**a) for a in accounts.get('results')]
	#
	# @classmethod
	# def order(cls, order: Order):
	# 	url = f'{COZA_HOST}/users/{cls.user_uuid}/excAcnts/{order.account.uuid}/order'
	# 	payload = {
	# 		'order_type': order.order_type,
	# 		'currency': order.currency,
	# 		'fiat': order.fiat,
	# 		'price': order.price,
	# 		'quantity': order.quantity
	# 	}
	# 	result = _request(url, 'POST', cls.user_uuid, data=payload)
	# 	return result

	# bot의 order api
	@classmethod
	def order(cls, order: Order):
		url = f'{COZA_HOST}/users/{cls.user_uuid}/bots/{cls.bot_id}/order'
		result = _request(url, 'POST', cls.user_uuid, data={'order_type': order.order_type,
													'currency': order.currency,
													'fiat': order.fiat,
													'quantity': order.quantity,
													'price': order.price,
													'is_safety': order.is_safety})
		return result

	# bot의 order 목록 조회 api
	@classmethod
	def order_list(cls, currency):
		url = f'{COZA_HOST}/users/{cls.user_uuid}/bots/{cls.bot_id}/orderlist'
		result = _request(url, 'POST', cls.user_uuid, data={'currency': currency})
		return result

	# bot의 order 취소 api
	@classmethod
	def order_cancel(cls, order_type, order_id, currency, fiat, price, quantity):
		url = f'{COZA_HOST}/users/{cls.user_uuid}/bots/{cls.bot_id}/ordercancel'
		result = _request(url, 'POST', cls.user_uuid, data={'order_type': order_type,
													'currency': currency,
													'fiat': fiat,
													'quantity': quantity,
													'price': price,
													'order_id':order_id})
		return result

	# bot의 완료된 order 조회 api
	@classmethod
	def order_complete(cls, currency):
		url = f'{COZA_HOST}/users/{cls.user_uuid}/bots/{cls.bot_id}/ordercomplete'
		result = _request(url, 'POST', cls.user_uuid, data={'currency': currency})
		return result

	# bot의 order 상태 조회 api
	@classmethod
	def order_status(cls, currency, order_id):
		url = f'{COZA_HOST}/users/{cls.user_uuid}/bots/{cls.bot_id}/orderstatus'
		result = _request(url, 'POST', cls.user_uuid, data={'currency': currency,
															'order_id': order_id})
		if result['info'] is not None:
			result['info']['currency'] = result['info']['currency'].lower()
			result['info']['fee'] = float(result['info']['fee'])
			result['info']['feeRate'] = float(result['info']['feeRate'])
			result['info']['price'] = float(result['info']['price'])
			result['info']['qty'] = round(float(result['info']['qty']), 3)
			result['info']['remainQty'] = round(float(result['info']['remainQty']), 3)
			result['info']['timestamp'] = int(result['info']['timestamp'])

		return result

	# bot의 정보 조회 api
	@classmethod
	def bot_info(cls):
		url = f'{COZA_HOST}/users/{cls.user_uuid}/bots/{cls.bot_id}'
		data = _request(url, 'GET', cls.user_uuid)
		return data

	# bot이 사용중인 model code 조회 api
	@classmethod
	def bot_code(cls):
		url = f'{COZA_HOST}/users/{cls.user_uuid}/bots/{cls.bot_id}/code'
		data = _request(url, 'GET', cls.user_uuid)
		return data

	# bot의 화폐 및 원화 조회 api
	'''
		사용법
		GET(조회) : TradeApi.bot_quantity()
		PUT(추가 또는 갱신) : TradeApi.bot_quantity(data={
											'use_balance': 128,
											'exchange': 'coinone',
											'fiat': 'krw',
											'currency': 'iota',
											'avail': 0.0,
											'balance': 2.7276670}
										)
	'''
	@classmethod
	def bot_quantity(cls, data=None):
		url = f'{COZA_HOST}/users/{cls.user_uuid}/bots/{cls.bot_id}/quantity'
		if data:
			result = _request(url, 'PUT', cls.user_uuid, data=data)
		else:
			result = _request(url, 'GET', cls.user_uuid)
		return result

	# bot history 조회 api
	'''
		'signal_type' = models.CharField(verbose_name='시그널 타입', max_length=10,
			choices=(('CANCEL', '주문취소'), ('TRADE', '거래'), ('FILLED', '체결'), ('START', '시작'), ('STOP', '중지'), ('ERROR', '에러')))
		trade_type = models.CharField(verbose_name='매수/매도', max_length=4, null=True, blank=True,
			choices=(('BUY', '매수'), ('SELL', '매도')))
		currency = models.CharField(verbose_name='화폐', max_length=20, null=True, blank=True)
		price = models.FloatField(verbose_name='평균체결가', null=True, blank=True)
		quantity = models.FloatField(verbose_name='주문수량', null=True, blank=True)
		eval_balance = models.FloatField(verbose_name='평가금액', null=True, blank=True)
		profit = models.FloatField(verbose_name='수익률', null=True, blank=True)
		is_safety = models.NullBooleanField(verbose_name='safety 여부')
		error_message = models.TextField(verbose_name='에러 메세지', null=True, blank=True)
	'''
	@classmethod
	def bot_signals(cls, data=None):
		url = f'{COZA_HOST}/users/{cls.user_uuid}/bots/{cls.bot_id}/signals'
		if data:
			result = _request(url, 'PUT', cls.user_uuid, data=data)
		else:
			result = _request(url, 'GET', cls.user_uuid)
		return result

	# bot 수익률 history 조회 api
	'''
		사용법
		GET(조회) : TradeApi.bot_profits()
		POST(추가) : TradeApi.bot_profits(data={
										'use_balance': 1000,
										'profit_rate': 5,
										'create_time': 14546786
									})
	'''
	@classmethod
	def bot_profits(cls, data=None):
		url = f'{COZA_HOST}/users/{cls.user_uuid}/bots/{cls.bot_id}/profits'
		if data:
			result = _request(url, 'POST', cls.user_uuid, data=data)
		else:
			result = _request(url, 'GET', cls.user_uuid)
		return result

	# oder에 대한 error 발생시 history 저장 api
	@classmethod
	def error(cls, error_msg, stop_bot=False):
		url = f'{COZA_HOST}/users/{cls.user_uuid}/bots/{cls.bot_id}/error'
		data = _request(url, 'POST', cls.user_uuid, data={'error_message': error_msg, 'stop_on_error': stop_bot})
		return data

	# user의 api key 조회 api
	# excAcnt_uuid = bot_info 조회시 리턴되는 exchange_account 딕셔너리 안의 uuid값
	'''
		KEY_COZA_USER_UUID = 'ca46c107-1029-47a8-bf84-320ee56b891f'
		BOT_ID = 147
		TradeApi.initialize(KEY_COZA_USER_UUID, BOT_ID)
		bot_info = TradeApi.bot_info()
		api_wrapper = TradeApi.get_user_excAcnt(bot_info['exchange_account']['uuid'])
	'''
	@classmethod
	def get_user_excAcnt(cls, excAcnt_uuid):
		url = f'{COZA_HOST}/users/{cls.user_uuid}/excAcnts/{excAcnt_uuid}'
		data = _request(url, 'GET', cls.user_uuid)
		return dict(
			result=True, exchange=data['exchange'],
			api_key=data['api_key'], secret_key=data['secret_key']
		)


class BacktestApi(object):
	@classmethod
	def initialize(cls, user_uuid):
		cls.user_uuid = user_uuid

	# model_name에 해당하는 model의 정보조회 api
	@classmethod
	def get_model(cls, model_name):
		url = f'{COZA_HOST}/botmodel/{model_name}'
		data = _request(url, 'GET', cls.user_uuid)
		return data

	@classmethod
	def get(cls, test_id):
		url = f'{COZA_HOST}/backtests/{test_id}'
		data = _request(url, 'GET', cls.user_uuid)
		return data

	'''
		result_data = {
			'model_id': model_id
			'created_time': create_time,
			'backtest_type': (day, week, month)
			'start_date':  start_date,
			'end_date': end_date,
			'init_budget': init_budget,
			'final_balance': final_balance,
			'total_fee': total_fee,
			'total_slippage': total_slippage,
			'fee_rate': fee_rate,
			'slippage_rate': slippage_rate,
			'earning_rate': earning_rate,
			'max_profit': max_profit,
			'max_loss': max_loss,
			'estimated_li': [
								{
									'date' : date,
									'estimated' : estimated
								},
								.
								.
								.
							]
		}
	'''
	# backtest 결과값 저장 api
	@classmethod
	def result(cls, result_data):
		url = f'{COZA_HOST}/backtests'
		data = _request(url, 'POST', cls.user_uuid, data={'result': result_data})
		return data
