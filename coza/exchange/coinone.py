from .base_exchange import TradeBase, BacktestBase
from datetime import datetime, timedelta
from coza.api.exchange import CoinoneAPIWrapper
from coza.api import CandleApi, ExchangeApi, TradeApi
from coza.errors import InputValueValidException
from coza.objects import Order
from coza.utils import truncate, KST
from coza.logger import logger
from copy import deepcopy
from collections import defaultdict
from time import sleep

import pandas as pd
import math
import sys
import os


NAME = "coinone"
MINIMUM_CURRENCY_QTY = {
    'btc': 0.0001,
    'eth': 0.001,
    'xrp': 1,
    'bch': 0.001,
    'eos': 0.1,
    'iota': 1,
    'qtum': 0.1,
    'zil': 1,
    'etc': 0.1,
    'data': 1,
    'ltc': 0.1,
    'omg': 0.1,
    'xtz': 0.1,
    'btg': 0.01,
    'knc': 1,
    'zrx': 1
}
MINIMUM_TRADE_PRICE = 500
CURRENCY_LIST = {'bch', 'btc', 'btg', 'data', 'eos', 'etc',
                 'eth', 'iota', 'knc', 'ltc', 'omg', 'qtum',
                 'xrp', 'xtz', 'zil', 'zrx'}
INTERVAL_LIST = {1, 3, 5, 15, 30, 60, 120, 240, 1440}
FIAT = {'krw',}
FEE_RATE = 0.001
SLIPPAGE_RATE = 0.002
R_OFF = 7


class CoinoneTrade(TradeBase):
    fee_rate=FEE_RATE
    def __init__(self, api_key, secret_key, init_budget, currency_list, interval_list, fiat, use_data, data_path,
                 running_mode='LIVE', using_api='CATSLAB'):
        if running_mode == 'LOCAL':
            if isinstance(api_key, str):
                self.api_key = api_key
            else:
                raise InputValueValidException(msg='Coinone Init', api_key=api_key)
                
            if isinstance(secret_key, str):
                self.secret_key = secret_key
            else:
                raise InputValueValidException(msg='Coinone Init', secret_key=secret_key)
        if using_api == 'EXCHANGE':
            self.api = CoinoneAPIWrapper(api_key=self.api_key, secret_key=self.secret_key)
            
        self.running_mode = running_mode
        if set(currency_list) != set(currency_list) & CURRENCY_LIST:
            raise InputValueValidException(msg='Coinone Init', currency=currency_list)
        if set(interval_list) != set(interval_list) & INTERVAL_LIST:
            raise InputValueValidException(msg='Coinone Init', interval=interval_list)
        if fiat.lower() not in FIAT:
            raise InputValueValidException(msg='Coinone Init Fiat', fiat=fiat)
        if using_api in ('EXCHANGE', 'CATSLAB'):
            self.using_api = using_api
        else:
            raise InputValueValidException(msg='Coinone Init', using_api=using_api)

        super().__init__(
            name=NAME, init_budget=init_budget, currency_list=currency_list, interval_list=interval_list,
            use_data=use_data, data_path=data_path, tz=KST, r_off=R_OFF, fiat=fiat)
        self.init_balance()
        self.data = dict()
        self.orders = defaultdict(list)
        self.ubtime = 0.0
        self.delay_time = 0.0
        self.fee_rate = FEE_RATE
        self.order_list = {f'{currency}': dict() for currency in currency_list}
        

    def update_balance(self):

        update_type = "FILLED"

        # Todo
        # 계산 시간 추가하기
        # Order를 전송하는 중간에 sleep하기

        if self.order_list.keys():
            for currency in self.order_list.keys():
                if self.order_list[currency].keys():
                    try:
                        if self.using_api == 'EXCHANGE':
                            c_order = self.api.order_complete(currency=currency)
                        elif self.using_api == 'CATSLAB':
                            c_order = TradeApi.order_complete({'currency':currency})
                    except Exception as e:
                        logger.critical(msg=e)
                        self.exit(msg=e, stop_bot=True)

                    """ Order_list / key= order_id
                        'currency': stat_re.get('currency'),
                        'price': stat_re.get('price'),
                        'quantity': stat_re.get('qty'),
                        'order_type': order.order_type,
                        'fiat': order.fiat,
                        'datetime': [datetime.fromtimestamp(int(stat_re.get('timestamp')))],
                        'remain_qty': stat_re.get('qty'),
                        'fee': round(stat_re.get('qty') * FEE_RATE, R_OFF) if order.order_type == 'BUY' else
                        math.ceil(int(stat_re.get('qty') * stat_re.get('price')) * FEE_RATE)
                    """

                    """ Update Quantity
                        update_type, order_id,  currency,  
                        order_type, use_balance, avail, balance
                    """

                    if c_order.get('result') == 'success' or c_order.get('result'):
                        pop_q = set()
                        for order_id in self.order_list[currency].keys():
                            recent_datetime = self.order_list[currency][order_id].get('datetime')[-1]
                            c_order_list = c_order.get('info') if 'info' in c_order else c_order.get('completeOrders')
                            for _order in c_order_list:
                                if recent_datetime > datetime.fromtimestamp(int(_order.get('timestamp'))):
                                    break

                                elif order_id == _order.get('orderId').lower() and \
                                        recent_datetime != datetime.fromtimestamp(int(_order.get('timestamp'))):
                                    _o = {
                                        'fee': float(_order.get('fee')),
                                        'order_id': _order.get('orderId').lower(),
                                        'price': int(float(_order.get('price'))),
                                        'qty': float(_order.get('qty')),
                                        'datetime': datetime.fromtimestamp(int(_order.get('timestamp'))),
                                        'type': 'SELL' if _order.get('type') == 'ask' else 'BUY'
                                    }
                                    self.order_list[currency][order_id]['fee'] -= _o.get('fee')
                                    self.order_list[currency][order_id]['remain_qty'] -= _o.get('qty')
                                    self.order_list[currency][order_id]['fee'] = round(self.order_list[currency][order_id]['fee'], R_OFF)
                                    self.order_list[currency][order_id]['remain_qty'] = round(self.order_list[currency][order_id]['remain_qty'], R_OFF)

                                    if _o.get('type') == 'SELL':
                                        self._update_quantity(
                                            update_type=update_type, order_id=order_id, currency=currency,
                                            order_type='SELL', price=_o.get('price'), quantity=_o.get('qty'),
                                            use_balance= round((_o.get('qty') * _o.get('price')) - _o.get('fee'), R_OFF), 
                                            avail=0, balance=-round(_o.get('qty') , R_OFF))

                                    elif _o.get('type') == 'BUY':
                                        self._update_quantity(
                                            update_type=update_type, order_id=order_id, currency=currency,
                                            order_type='BUY', price=_o.get('price'), quantity=_o.get('qty'),
                                            use_balance=0, avail=_o.get('qty') - _o.get('fee'), balance=0)

                                    self.order_list[currency][order_id]['datetime'].append(_o.get('datetime'))
                                    if self.order_list[currency][order_id]['remain_qty'] == 0:
                                        if _o.get('type') == 'SELL':
                                            self.balance['fiat'] += self.order_list[currency][order_id].get('fee')
                                        elif _o.get('type') == 'BUY':
                                            self.balance[currency]['balance'] -= self.order_list[currency][order_id].get('fee')

                                        pop_q.add(order_id)

                        for pop_i in pop_q:
                            self.order_list[currency].pop(pop_i)
                    else:
                        return 0


    def _send_order(self, order, _datetime=None):
        order_re = None
        update_type = "ORDER"

        if order.order_type == 'BUY':
            if self.balance['fiat'] - order.price * order.quantity < 0:
                logger.debug(f'[ORDER_FAILED] Failed to send order because of \'Lack of Balance\' : {order}')
                return dict(error='Bigger than fiat')
            elif order.quantity * order.price < MINIMUM_TRADE_PRICE:
                logger.debug(f'[ORDER_FAILED] Failed to send order because of \'Minimum Trade Price\' : {order}')
                return dict(error='Minimum order price is 500 KRW')
            elif order.quantity < MINIMUM_CURRENCY_QTY[order.currency]:
                logger.debug(f'[ORDER_FAILED] Failed to send order because of \'Minimum Currency Quantity\' : {order}')
                return dict(error='Lower than minimum quantity')
            else:
                try:
                    if self.using_api == 'EXCHANGE':
                        order_re = self.api.order_buy(
                            currency=order.currency, fiat=self.fiat, price=order.price, quantity=order.quantity)
                    elif self.using_api == 'CATSLAB':
                        order_re = TradeApi.order(
                            {
                                'order_type': order.order_type,
                                'currency': order.currency,
                                'fiat': self.fiat,
                                'quantity': order.quantity,
                                'price': order.price,
                            })
                except Exception as e:
                    logger.error(msg=e)
                    self._send_error(msg=e)
        elif order.order_type == 'SELL':
            if self.balance[order.currency]['avail'] - order.quantity < 0:
                logger.debug(f'[ORDER_FAILED] Failed to send order because of \'Lack of Balance\' : {order}')
                return dict(error='Lack of Balance')
            elif order.quantity * order.price < MINIMUM_TRADE_PRICE:
                logger.debug(f'[ORDER_FAILED] Failed to send order because of \'Minimum Trade Price\' : {order}')
                return dict(error='Minimum order price is 500 KRW')
            elif order.quantity < MINIMUM_CURRENCY_QTY[order.currency]:
                logger.debug(f'[ORDER_FAILED] Failed to send order because of \'Minimum Currency Quantity\' : {order}')
                return dict(error='Minimum Currency Quantity')
            else:
                try:
                    if self.using_api == 'EXCHANGE':
                        order_re = self.api.order_sell(
                            currency=order.currency, fiat=self.fiat, price=order.price, quantity=order.quantity)
                    elif self.using_api == 'CATSLAB':
                        order_re = TradeApi.order(
                            {
                                'order_type': order.order_type,
                                'currency': order.currency,
                                'fiat': self.fiat,
                                'quantity': order.quantity,
                                'price': order.price
                            })
                except Exception as e:
                    self._send_error(msg=e)
        else:
            return False

        if order_re.get('order_id'):
            logger.debug(f'[ORDER] Successfully sended order : {order}')
            # Todo
            # 2차
            # 1. Add Logger: Success Order
            # 2. Order를 전송하기 전에
            # 3. 어떤 가상화폐를 먼저 처리할 건지
            # 4. BUY 먼저 할지 SELL 먼저 할지
            # 5. order_result와 order가 일치하는지.

            order_id = order_re.get('order_id')
            sleep(0.04)
            try:
                if self.using_api == 'EXCHANGE':
                    stat_re = self.api.order_status(currency=order.currency, order_id=order_id)
                elif self.using_api == 'CATSLAB':
                    stat_re = TradeApi.order_status(
                        {
                            'currency': order.currency,
                            'order_id': order_id
                        })
            except Exception as e:
                logger.error(msg=e)
                self._send_error(msg=e)

            if stat_re.get('status', None) == 'filled':
                update_type = 'ORDER_FILLED'
                stat_re = {
                    'currency':  stat_re['info'].get('currency').lower(),
                    'price': int(float(stat_re['info'].get('price'))),
                    'qty': float(stat_re['info'].get('qty')),
                    'fee': float(stat_re['info'].get('fee')),
                    'timestamp': int(float(stat_re['info'].get('timestamp'))),
                    'type': stat_re['info'].get('type')
                }

                if order.order_type == 'SELL':
                    self._update_quantity(
                        update_type=update_type, order_id=order_re.get('order_id'), currency=order.currency,
                        use_balance=round((stat_re.get('qty') * stat_re.get('price')) - stat_re.get('fee'), R_OFF),
                        price=stat_re.get('price'), quantity=stat_re.get('qty'), order_type=order.order_type,
                        avail=-round(stat_re.get('qty'), R_OFF), balance=-round(stat_re.get('qty'), R_OFF))

                elif order.order_type == 'BUY':
                    self._update_quantity(
                        update_type=update_type, order_id=order_re.get('order_id'), currency=order.currency,
                        use_balance=-round(stat_re.get('price') * stat_re.get('qty'), R_OFF),
                        price=stat_re.get('price'), quantity=stat_re.get('qty'), order_type=order.order_type,
                        avail= round(stat_re.get('qty') - stat_re.get('fee'), R_OFF),
                        balance=round(stat_re.get('qty') - stat_re.get('fee'), R_OFF))

            elif stat_re.get('status', None) == 'live':
                stat_re = {
                    'currency': stat_re['info'].get('currency').lower(),
                    'price': int(float(stat_re['info'].get('price'))),
                    'qty': float(stat_re['info'].get('qty')),
                    'timestamp': int(float(stat_re['info'].get('timestamp'))),
                    'type': stat_re['info'].get('type')
                }

                self.order_list[f'{order.currency}'][f'{order_id}'] = {
                    'currency': stat_re.get('currency'),
                    'price': stat_re.get('price'),
                    'quantity': stat_re.get('qty'),
                    'order_type': order.order_type,
                    'fiat': order.fiat,
                    'datetime': [datetime.fromtimestamp(int(stat_re.get('timestamp')))],
                    'remain_qty': stat_re.get('qty'),
                    'fee': round(stat_re.get('qty') * FEE_RATE, R_OFF) if order.order_type == 'BUY' else
                    round(int(stat_re.get('qty') * stat_re.get('price')) * FEE_RATE, R_OFF)
                }

                if order.order_type == 'SELL':
                    self._update_quantity(
                        update_type=update_type, order_id=order_re.get('order_id'), use_balance=0, currency=order.currency,
                        order_type=order.order_type, price=stat_re.get('price'), quantity=stat_re.get('qty'),
                        avail=-round(stat_re.get('qty'), R_OFF), balance=0)
                elif order.order_type == 'BUY':
                    self._update_quantity(
                        update_type=update_type, order_id=order_re.get('order_id'), currency=order.currency,
                        use_balance=-round(stat_re.get('price') * stat_re.get('qty'), R_OFF), order_type=order.order_type,
                        price=stat_re.get('price'), quantity=stat_re.get('qty'),
                        avail=0, balance=round(stat_re.get('qty') * (1 - FEE_RATE), R_OFF))
            else:
                logger.debug(f'[ORDER_FAILED] Failed to send order : {order}')
                return dict(error="Failed To Send Order")

            return dict(error="Order Completed")

        else:
            logger.debug(f'[ORDER_FAILED] Failed to send order : {order}')
            logger.info(f'order_re : {order_re}')
            return dict(error="Failed To Send Order")


    def _send_cancel(self, currency, order_id, qty=None):
        update_type = "CANCEL"
        cancel_result = False
        update_result = False

        try:
            if self.using_api == 'CATSLAB':
                order_stat = TradeApi.order_status(
                    {
                        'currency': currency,
                        'order_id': order_id
                    })
            elif self.using_api == 'EXCHANGE':
                order_stat = self.api.order_status(currency=currency, order_id=order_id)
        except Exception as e:
            logger.error(msg=e)
            self._send_error(msg=e)
            
        if self.using_api == 'CATSLAB':
            if order_stat == 'Order id is not exist':
                logger.debug('[CANCEL_FAILED] 해당 order_id는 존재하지 않습니다.')
                return True
        elif self.using_api == 'EXCHANGE':
            if order_stat.get('status', None) is None:
                logger.debug('[CANCEL_FAILED] 해당 order_id는 존재하지 않습니다.')
                return True
        
        order_c = self.order_list[currency][order_id]
        remainQty = truncate(round(float(order_stat['info']['remainQty']), R_OFF), 4)
        
        if order_stat['status'] == 'filled':
            logger.debug(f'[ORDER_FILLED] Already filled order {order_id} : {self.order_list[currency][order_id]}')
            
            update_type = "FILLED"
            if order_c['order_type'] == 'BUY':
                self._update_quantity(
                    update_type=update_type, order_id=order_id, use_balance=0, currency=currency,
                    order_type=order_c['order_type'], price=order_c['price'], quantity=order_c['quantity'],
                    avail=round(order_c['remain_qty']*(1-FEE_RATE), R_OFF), balance=0)

            elif order_c['order_type'] == 'SELL':
                use_balance = round((order_c['remain_qty']*order_c['price'])*(1-FEE_RATE), R_OFF)
                self._update_quantity(
                    update_type=update_type, order_id=order_id, use_balance=use_balance, currency=currency,
                    order_type=order_c['order_type'], price=order_c['price'], quantity=order_c['quantity'],
                    avail=0, balance=-round(order_c['remain_qty'], R_OFF))

            return True

        elif order_stat['status'] == 'live':
            logger.debug(f'[ORDER_LIVE] Still live order {order_id} : {order_c}')
            
            if qty is None:
                quantity_c = remainQty
            else:
                if qty < remainQty:
                    quantity_c = truncate(round(qty, R_OFF), 4)
#                     if (remainQty - quantity_c) * order_c['price'] < MINIMUM_TRADE_PRICE:
#                         logger.debug(f'[ORDER_CANCEL_FAILED] Failed to cancel order because of \'Minimum Trade Price\' {order_id} : {order_c}')
#                         return False
                else:
                    quantity_c = remainQty
            try:
                if self.using_api == 'CATSLAB':
                    cancel_result = TradeApi.order_cancel(
                        {
                            'order_type': order_c['order_type'],
                            'currency': currency,
                            'fiat': self.fiat,
                            'quantity': quantity_c,
                            'price': order_c['price'],
                            'order_id':order_id  
                        })
                elif self.using_api == 'EXCHANGE':
                    cancel_result = self.api.order_cancel(currency=currency, order_id=order_id, order_type=order_c['order_type'],
                                                          fiat='krw', price=order_c['price'], quantity=quantity_c)
            except Exception as e:
                logger.error(msg=e)
                self._send_error(msg=e)
                return dict(error=e)

            if cancel_result['result'] == 'success':
                logger.debug(f'[ORDER_CANCELED] Successfully canceled order : {order_c}')
                logger.info(f'Canceled quantity : {quantity_c} out of {remainQty}')
                if order_c['order_type'] == 'BUY':
                    price = int(float(order_stat['info']['price']))
                    use_balance = round(quantity_c * price, R_OFF)
                    self._update_quantity(
                        update_type=update_type, order_id=order_id, use_balance=use_balance, currency=currency,
                        order_type=order_c['order_type'], price=order_c['price'], quantity=order_c['quantity'],
                        avail=0, balance=-round(quantity_c * (1-FEE_RATE), R_OFF))
                # SELL
                elif order_c['order_type'] == 'SELL':
                    self._update_quantity(
                        update_type=update_type, order_id=order_id, use_balance=0, currency=currency,
                        order_type=order_c['order_type'], price=order_c['price'], quantity=order_c['quantity'],
                        avail=round(quantity_c, R_OFF), balance=0)

                if qty is None or qty >= remainQty:
                    return True
                elif qty < remainQty:
                    self.order_list[currency][order_id]['fee'] -= round(quantity_c * FEE_RATE, R_OFF)
                    self.order_list[currency][order_id]['fee'] = round(self.order_list[currency][order_id]['fee'], R_OFF)
                    self.order_list[currency][order_id]['remain_qty'] -= qty
                    self.order_list[currency][order_id]['remain_qty'] = round(self.order_list[currency][order_id]['remain_qty'], R_OFF)
                    return False

            else:
                logger.debug(f'[ORDER_CANCEL_FAILED] Failed to cancel order {order_id} : {order_c}')
                return False


    def set_cancel(self, currency=None, order_id=None, qty=None):
        if currency not in CURRENCY_LIST and currency is not None:
            raise InputValueValidException(c_func='set_cancel', param_='currency', value_=currency)

        if qty is None:
            if order_id is None and currency is None:
                logger.debug('Canceling all orders which are not filled...')

                for _currency in self.currencies:
                    if self.order_list[_currency].keys():
                        logger.info(f'order_list to cancel : {self.order_list[_currency]}')
                        pop_q = set()
                        for _order_id in self.order_list[_currency].keys():
                            logger.debug(f'Canceling order {_order_id} : {self.order_list[_currency][_order_id]}')
                            if self._send_cancel(currency=_currency, order_id=_order_id):
                                pop_q.add(_order_id)

                        for item in pop_q:
                            self.order_list[_currency].pop(item)

            elif order_id is None:
                logger.debug(f'Canceling all orders of {currency}...')
                logger.info(f'order_list to cancel : {self.order_list[currency]}')

                if self.order_list[currency].keys():
                    pop_q = set()
                    for _order_id in self.order_list[currency].keys():
                        logger.info(f'Canceling order {_order_id} : {self.order_list[currency][_order_id]}')
                        if self._send_cancel(currency=currency, order_id=_order_id):
                            pop_q.add(_order_id)

                    for item in pop_q:
                        self.order_list[currency].pop(item)
                else:
                    logger.debug(f'입력하신 {currency}에 대한 주문이 없습니다.')

            elif order_id is not None and currency is None:
                logger.debug('currency를 함께 입력해야 합니다.')
            else:
                logger.debug(f'Canceling order {order_id}...')
                if order_id in self.order_list[currency].keys():
                    logger.info(f'order to cancel : {self.order_list[currency][order_id]}')
                    if self._send_cancel(currency=currency, order_id=order_id):
                        self.order_list[currency].pop(order_id)
                else:
                    logger.debug(f'입력하신 order_id {order_id}가 존재하지 않습니다.')

        else:
            qty = truncate(qty, 4)

            if currency is None or order_id is None:
                logger.debug('currency와 order_id를 함께 입력해야 합니다.')

            else:
                logger.debug(f'Canceling order {order_id} with quantity {qty}...')
                if order_id in self.order_list[currency].keys():
                    logger.info(f'order to cancel : {self.order_list[currency][order_id]}')
                    if self._send_cancel(currency=currency, order_id=order_id, qty=qty):
                        self.order_list[currency].pop(order_id)
                else:
                    logger.debug(f'입력하신 order_id {order_id}가 존재하지 않습니다.')


    def calc_estimated(self):
        estimated = 0
        currency_estimated = 0
        _balance = deepcopy(self.balance)

        # 체결되지 않은 주문에 대한 추정금 계산.
        if self.order_list.keys():
            for currency in self.order_list.keys():
                for order in self.order_list[currency].keys():
                    order_c = self.order_list[currency].get(order)

                    if order_c.get('order_type') == 'BUY':
                        estimated += round(order_c['price'] * order_c['quantity'], R_OFF)
                        _balance[order_c['currency']]['balance'] -= order_c['quantity']

        for k in _balance.keys():
            if k == 'fiat':
                estimated += _balance[k]
            else:
                sleep(0.035)
                try:
                    current_orderbook = self.get_orderbook(currency=k)

                except Exception as e:
                    logger.critical(msg=e)
                    self.exit(msg=e)
                currency_estimated += round(_balance[k]['balance'] * current_orderbook['bid_price'][0], R_OFF)

        self.estimated = estimated + currency_estimated
        self.currency_ratio = round(currency_estimated / self.estimated, R_OFF)
        self.earning_rate = round((estimated - self.init_budget) / self.init_budget, R_OFF)
        return dict(estimated=self.estimated, currency_ratio=self.currency_ratio, earning_rate=self.earning_rate)


    def clear_balance(self):
        self.set_cancel()
        for k in self.balance.keys():
            if k == 'fiat':
                continue
            else:
                try:
                    if self.using_api == 'EXCHANGE':
                        price = self.api.get_orderbook(currency=k, fiat=self.fiat, limit=30)['orderbook']['bid_price'][0]
                    elif self.using_api == 'CATSLAB':
                        price = ExchangeApi.get_orderbook(exchange=NAME, currency=k)['orderbook']['bid_price'][0]
                    self._send_order(
                        Order(
                            exchange=NAME, currency=k, order_type='SELL', fiat=self.fiat, price=price, quantity=self.balance[k]['balance'])
                    )
                except Exception as e:
                    logger.error(msg=e)
                    self._send_error(msg=e)


    def get_orderbook(self, currency):
        try:
            if self.using_api == 'CATSLAB':
                orderbook = pd.DataFrame(ExchangeApi.get_orderbook(exchange=NAME, currency=currency)['orderbook'])
            elif self.using_api == 'EXCHANGE':
                orderbook = self.api.get_orderbook(currency=currency, fiat=self.fiat, limit=20)['orderbook']
        except Exception as e:
            logger.error(e)
            self._send_error(msg=e)
            return dict(error=e)

        return orderbook


class CoinoneBacktest(BacktestBase):
    fee_rate = FEE_RATE

    def __init__(self, start_date, end_date, init_budget, currency_list, interval_list, fiat, slippage_rate=None,
                 use_data="LIVE", data_path='data'):
        self.name = NAME
        if slippage_rate is None:
            self.slippage_rate = SLIPPAGE_RATE
        else:
            self.slippage_rate = slippage_rate

        if isinstance(start_date, datetime):
            self.start_date = start_date.astimezone(KST)
        if isinstance(end_date, datetime):
            self.end_date = end_date.astimezone(KST)
        if use_data in ('LOCAL', 'LIVE'):
            self.use_data = use_data
        if not isinstance(init_budget, (int, float)):
            raise InputValueValidException(msg='Coinone Init', init_budget=init_budget)
        if set(currency_list) != set(currency_list) & CURRENCY_LIST:
            raise InputValueValidException(msg='Coinone Init', currency=currency_list)
        if set(interval_list) != set(interval_list) & INTERVAL_LIST:
            raise InputValueValidException(msg='Coinone Init', interval=interval_list)
        if fiat not in FIAT:
            raise InputValueValidException(mag='Coinone Init Fiat', fiat=fiat)
        if isinstance(data_path, str):
            self.data_path = data_path
        else:
            raise InputValueValidException(msg='Coinone Init', data_path=data_path)

        super().__init__(init_budget=init_budget, currency_list=currency_list, interval_list=interval_list, fiat=fiat)
        self.init_balance()
        self.data = dict()
        self.test_df = dict()
        self.estimated_list = list()
        self.order_list = defaultdict(list)
        self.trade_history = defaultdict(dict)
        self.next_idx = defaultdict(int)
        self.orders = defaultdict(list)
        self.total_fee = 0.0
        self.total_slippage = 0.0
        self.max_profit = 0.0
        self.max_loss = 0.0
        self.earning_rate = 0.0


    def init_dataframe(self):
        logger.debug('Preparing data...')
        
        forward_candle_frame = {
            1: 1440,
            3: 480,
            5: 288,
            15: 120,
            30: 120,
            60: 720,
            120: 150,
            240: 150,
            1440: 180
        }
        from_date = {}
        until_date = {}

        for interval in self.intervals:
            from_date[interval] = self.start_date - timedelta(minutes=interval * forward_candle_frame[interval])
            until_date[interval] = self.end_date - timedelta(minutes=interval)

        if self.use_data == 'LOCAL':
            path = f'{self.data_path}/{NAME}'

        for currency in self.currencies:
            for interval in self.intervals:
                if self.use_data == 'LIVE':
                    try:
                        df = CandleApi.get_df(
                            exchange=NAME, currency=currency, fiat=self.fiat, interval=interval,
                            from_date=from_date[interval], until_date=until_date[interval])
                        df['datetime'] = [datetime.fromtimestamp(t).astimezone(KST) for t in df['timestamp']]
                        df.set_index(keys='datetime', inplace=True)
                        self.data[f'{currency}_{interval}'] = df
                    except Exception as e:
                        logger.info(f'Sorry, Candle dataframe initialize failed by {e}. And system out.')
                        sys.exit()

                elif self.use_data == 'LOCAL':
                    filename = f'{currency}_{interval}_{self.fiat}.csv'
                    try:
                        df = pd.read_csv(os.path.join(path, filename)).sort_values(by=['timestamp'])
                    except FileNotFoundError:
                        print(f"{filename} 파일이 존재하지 않습니다.")

                    self.data[f'{currency}_{interval}'] = \
                        df[df[df['timestamp'] >= datetime.timestamp(from_date[interval])].index[0]:
                           df[df['timestamp'] <= datetime.timestamp(self.end_date)].index[-1]]
                    self.data[f'{currency}_{interval}']['datetime'] = \
                        [datetime.fromtimestamp(t).astimezone(KST) for t in self.data[f'{currency}_{interval}']['timestamp']]
                    self.data[f'{currency}_{interval}'].set_index(keys='datetime', inplace=True)
                    del(df)

                self.updated_len[f'{currency}_{interval}'] = len(self.data[f'{currency}_{interval}'])
                logger.debug(f'Prepared candle data {currency}_{interval}')
                df_len = len(self.data[f'{currency}_{interval}'])
                logger.info(f'length of {currency}_{interval} : {df_len}')
                

    def init_test_dataframe(self):
        logger.debug('Initializing dataframe...')
        
        self.test_df = self.data
        self.data = {}
        for curr_inter in self.test_df.keys():
            interval = int(curr_inter.split('_')[1])
            self.data[curr_inter] = self.test_df[curr_inter][:self.start_date - timedelta(minutes=2*interval)]


    def update_dataframe(self, _datetime):
        has_updated = False
        for curr_inter in self.data.keys():

            try:
                interval = int(curr_inter.split('_')[1])
                df = self.test_df[curr_inter].loc[_datetime - timedelta(minutes=interval)]
            except KeyError:
                self.updated_len[curr_inter] = 0
            else:
                self.updated_len[curr_inter] = len(df)
                self.data[curr_inter] = self.data[curr_inter].append(df)
                has_updated = True

        return has_updated


    def init_balance(self):
        self.balance = dict(
            fiat=self.init_budget
        )
        for currency in self.currencies:
            self.balance[currency] = {
                'avail': 0.0,
                'balance': 0.0
            }

    def update_balance(self, _datetime):
        df_datetime = _datetime
        pop_q = set()

        if self.orders.keys():
            for order_t in self.orders.keys():
                if order_t <= self.start_date:
                    pop_q.add(order_t)

                elif order_t <= df_datetime:
                    for order in self.orders[order_t]:
                        result = self._send_order(order, order_t)
                        if result.get('error'):
                            logger.debug("Order Fail MSG: {}".format(result.get('msg')))
                        pop_q.add(order_t)

        for i in pop_q:
            self.orders.pop(i)

        pop_q.clear()

        if self.order_list.keys():
            estimated_dict = self.calc_estimated()
            for k in self.order_list.keys():
                self.estimated_list.append({'date': k, 'estimated': round(estimated_dict.get('estimated'), 4)})
                self.trade_history[k] = {
                    'order_list': self.order_list[k],
                    'balance': deepcopy(self.balance),
                    'estimated': estimated_dict.get('estimated'),
                    'earning_rate': estimated_dict.get('earning_rate')
                }

                pop_q.add(k)

            self.max_profit = estimated_dict.get('earning_rate') if estimated_dict.get('earning_rate') > self.max_profit else self.max_profit
            self.max_loss = estimated_dict.get('earning_rate') if estimated_dict.get('earning_rate') < self.max_loss else self.max_loss

        for i in pop_q:
            self.order_list.pop(i)

        return True


    def _send_order(self, order, _datetime=None):
        if order.price * order.quantity < MINIMUM_TRADE_PRICE:
            logger.debug(f'[ORDER_FAILED] Failed to send order because of \'Minimum Trade Price\' : {order}')
            return dict(error='Lower than minimum trade price')
        elif order.quantity < MINIMUM_CURRENCY_QTY[order.currency]:
            logger.debug(f'[ORDER_FAILED] Failed to send order because of \'Minimum Currency Quantity\' : {order}')
            return dict(error='Lower than minimum quantity')
        else:
            if order.order_type == 'BUY':
                if order.price * order.quantity <= self.balance['fiat']:
                    self.balance['fiat'] -= round(order.price * order.quantity, R_OFF)
                    self.balance[order.currency]['avail'] += round(order.quantity * (1 - (FEE_RATE + self.slippage_rate)), R_OFF)
                    self.balance[order.currency]['balance'] += round(order.quantity * (1 - (FEE_RATE + self.slippage_rate)), R_OFF)
                else:
                    logger.debug(f'[ORDER_FAILED] Failed to send order because of \'Lack of Balance\' : {order}')
                    return dict(error='Not enough Fiat.')
            elif order.order_type == 'SELL':
                if order.quantity <= self.balance[order.currency]['balance']:
                    self.balance['fiat'] += round(order.price * order.quantity * (1 - (FEE_RATE + self.slippage_rate)), R_OFF)
                    self.balance[order.currency]['avail'] -= order.quantity
                    self.balance[order.currency]['balance'] -= order.quantity
                else:
                    logger.debug(f'[ORDER_FAILED] Failed to send order because of \'Lack of Balance\' : {order}')
                    return dict(error='Not enough coin balance.')
            else:
                logger.debug(f'[ORDER_FAILED] Failed to send order because of \'Unknown OrderType\' : {order}')
                return dict(error='Unkown OrderType')

            self.total_fee += round(order.price * order.quantity * FEE_RATE, R_OFF)
            self.total_slippage += round(order.price * order.quantity * self.slippage_rate, R_OFF)
            self.order_list[self._get_df_datetime() if _datetime is None else _datetime].append(order)
            return dict(error='Send order complete')


    def set_order(self, o, t=None):
        c_func='set_order'
        if isinstance(t, type(None)):
            if isinstance(o, Order):
                return self._send_order(o)
            else:
                raise InputValueValidException(c_func=c_func, param_='o', value_=o)
        elif isinstance(t, datetime):
            if isinstance(o, Order):
                self.orders[t].append(o)
                return dict(error='Add Order Complete')
            else:
                raise InputValueValidException(c_func=c_func, param_='o', value_=o)
        else:
            raise InputValueValidException(c_func=c_func, param_='t', value_=t)


    def set_cancel(self, currency=None, order_id=None, qty=None):
        return dict(error='Backtest not support cancel.')


    def get_balance(self):
        return self.balance


    def get_order_list(self):
        return []


    def get_orders(self):
        return self.orders


    def get_time(self):
        return self._get_df_datetime()


    def _get_df_datetime(self):
        currency = self.currencies[0]
        datetime_dump = datetime.fromtimestamp(
            self.data[f'{currency}_{self.intervals[0]}']['timestamp'].iloc[-1]).astimezone(KST)

        if len(self.intervals) > 1:
            for interval in self.intervals[1:]:
                df_datetime = datetime.fromtimestamp(
                    self.data[f'{currency}_{interval}']['timestamp'].iloc[-1]).astimezone(KST)
                if df_datetime > datetime_dump:
                    datetime_dump = df_datetime

        return datetime_dump


    def calc_estimated(self):
        estimated = 0
        currency_estimated = 0

        for key in self.balance.keys():
            if key == 'fiat':
                estimated += self.balance[key]
            elif self.balance[key]['balance'] is not 0 or 0.0:
                currency_estimated += round(self.balance[key]['balance'] * self._get_currency_price(currency=key), R_OFF)

        estimated = round(estimated + currency_estimated, R_OFF)
        currency_ratio = round(currency_estimated / estimated, R_OFF)
        earning_rate = round((estimated - self.init_budget) / self.init_budget, R_OFF)

        return dict(estimated=estimated, currency_ratio=currency_ratio, earning_rate=earning_rate)



    def clear_balance(self):
        for k in self.balance.keys():
            if k == 'fiat':
                continue
            else:
                price = self._get_currency_price(currency=k)
                self._send_order(
                    Order(
                        currency=k, order_type='SELL', fiat=self.fiat, price=price,
                        quantity=self.balance[k]['balance'])
                )


    def _get_currency_price(self, currency):
        datetime_dump = datetime.fromtimestamp((self.data[f'{currency}_{self.intervals[0]}']['timestamp'].iloc[-1])).astimezone(KST)
        recently_df = f'{currency}_{self.intervals[0]}'

        if len(self.intervals) > 1:
            for interval in self.intervals:
                df_datetime = datetime.fromtimestamp(self.data[f'{currency}_{interval}']['timestamp'].iloc[-1]).astimezone(KST)
                if df_datetime > datetime_dump:
                    datetime_dump = df_datetime
                    recently_df = f'{currency}_{interval}'
        return self.data[recently_df]['close'].iloc[-1]


