from .base_exchange import BaseExchange
from datetime import datetime, timedelta
from coza.api.exchange import CoinoneAPIWrapper
from coza.api import CandleApi, TradeApi
from coza.objects import Order
from coza.utils import truncate
from copy import deepcopy
from collections import defaultdict
from time import sleep

import pandas as pd
import numpy as np
import math
import os

NAME = "coinone"
MINUMUM_CURRENCY_QTY = {
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
FEE_RATE = 0.001
SLIPPAGE_RATE = 0.002
R_OFF = 7


class CoinoneTrade(BaseExchange):
    name=NAME
    fee_rate=FEE_RATE

    def __init__(self, api_key, secret_key, init_budget, currency_list, interval_list, fiat, running_mode='LIVE'):
        super().__init__(init_budget=init_budget, currency_list=currency_list, interval_list=interval_list, fiat=fiat)
        self.api_key = api_key
        self.secret_key = secret_key
        self.running_mode = running_mode
        self.init_balance()
        self.data = dict()
        self.orders = defaultdict(list)
        self.ubtime = 0.0
        self.delay_time = 0.0
        self.order_list = {f'{currency}': dict() for currency in currency_list}
        self.api = CoinoneAPIWrapper(api_key=self.api_key, secret_key=self.secret_key)


    def init_dataframe(self):
        # Todo
        # updated_len
        until_date = {}
        time_now = datetime.now()

        for interval in self.intervals:
            until_date[interval] = time_now - timedelta(minutes=interval)

        for currency in self.currencies:
            for interval in self.intervals:
                # Todo
                # 2차
                # Add Logging: Initialize된 Candle Data

                df = CandleApi.get_df(
                    exchange=self.name, currency=currency, fiat=self.fiat,
                    interval=interval, until_date=until_date[interval])
                df['datetime'] = [datetime.fromtimestamp(t) for t in df['timestamp']]
                df.set_index(keys='datetime', inplace=True)
                self.data[f'{currency}_{interval}'] = df
                self.is_update[f'{currency}_{interval}'] = False
                self.updated_len[f'{currency}_{interval}'] = len(self.data[f'{currency}_{interval}'])


    def update_dataframe(self):
        decay_time = 0.0
        cur_date = datetime.now().replace(second=0, microsecond=0)

        while decay_time > -0.8:
            sleep_time = round(0.3 * np.random.rand() + 0.7, 3) + self.delay_time - decay_time
            sleep(sleep_time)

            for candle in self.data.keys():
                get_candle = False
                currency, interval = candle.split('_')
                interval = int(interval)

                if interval * 60 - ((cur_date - self.data[candle].index[-1]).total_seconds() - interval * 60) <= 0:
                    get_candle = True

                if get_candle:
                    df = CandleApi.get_df(
                        exchange=self.name, currency=currency, fiat=self.fiat, interval=interval,
                        from_date=self.data[candle].index[-1])
                    update_len = len(df) - 1

                    if update_len < 1:
                        print(update_len)
                        print(df)
                        print(self.data[candle].tail(5))
                        print(f'Get Candle Failed {self.data[candle].index[-1]}')
                        print(f'Time Now : {datetime.now()}')
                        print(f'Sleep Time is : {sleep_time}')

                        self.updated_len[candle] = 0
                        self.delay_time += 0.1
                        decay_time -= 0.2
                        break

                    else:
                        df['datetime'] = [datetime.fromtimestamp(t) for t in df['timestamp']]
                        df.set_index(keys='datetime', inplace=True)
                        df.drop(df.index[0], inplace=True)
                        self.updated_len[candle] = update_len
                        self.data[candle].drop(self.data[candle].index[range(self.updated_len[candle])], inplace=True)
                        self.data[candle] = self.data[candle].append(df)

                else:
                    self.updated_len[candle] = 0

            self.delay_time -= 0.2 if self.delay_time - 0.2 > 0.7 else self.delay_time
            return True

        return False


    def init_balance(self):
        self.balance = dict(
            fiat=self.init_budget
        )
        for currency in self.currencies:
            self.balance[currency] = {
                'avail': 0.0,
                'balance': 0.0
            }


    def update_balance(self):

        update_type = "FILLED"

        # Todo
        # 계산 시간 추가하기
        # Order를 전송하는 중간에 sleep하기

        if self.order_list.keys():
            for currency in self.order_list.keys():
                if self.order_list[currency].keys():
                    c_order = self.api.order_complete(currency=currency)
                    """ Order_list / key= order_id
                        'currency': stat_re.get('currency'),
                        'price': stat_re.get('price'),
                        'quantity': stat_re.get('qty'),
                        'order_type': order.order_type,
                        'fiat': order.fiat,
                        'timestamp': [stat_re.get('timestamp')],
                        'remain_qty': stat_re.get('qty'),
                        'fee': round(stat_re.get('qty') * FEE_RATE, R_OFF) if order.order_type == 'BUY' else
                        math.ceil(int(stat_re.get('qty') * stat_re.get('price')) * FEE_RATE)
                    """

                    """ Update Quantity
                        update_type, order_id,  currency,  
                        order_type, use_balance, avail, balance
                    """

                    if c_order.get('result') == 'success':
                        pop_q = set()
                        for order_id in self.order_list[currency].keys():
                            recent_timestamp = self.order_list[currency][order_id].get('timestamp')[-1]

                            for _order in c_order.get('info', []):
                                if recent_timestamp > int(_order.get('timestamp')):
                                    break

                                elif order_id == _order.get('orderId').lower() and \
                                        recent_timestamp != int(_order.get('timestamp')):
                                    _o = {
                                        'fee': float(_order.get('fee')),
                                        'order_id': _order.get('orderId').lower(),
                                        'price': int(_order.get('price')),
                                        'qty': float(_order.get('qty')),
                                        'timestamp': int(_order.get('timestamp')),
                                        'type': 'SELL' if _order.get('type') == 'ask' else 'BUY'
                                    }
                                    self.order_list[currency][order_id]['fee'] -= _o.get('fee')
                                    self.order_list[currency][order_id]['remain_qty'] -= _o.get('qty')

                                    if _o.get('type') == 'SELL':
                                        self._update_quantity(
                                            update_type=update_type, order_id=order_id, currency=currency,
                                            order_type='SELL', price=_o.get('price'), quantity=_o.get('qty'),
                                            use_balance= int(_o.get('qty') * _o.get('price')) - _o.get('fee'), avail=0,
                                            balance=-round(_o.get('qty') , R_OFF))

                                    elif _o.get('type') == 'BUY':
                                        self._update_quantity(
                                            update_type=update_type, order_id=order_id, currency=currency,
                                            order_type='BUY', price=_o.get('price'), quantity=_o.get('qty'),
                                            use_balance=0, avail=_o.get('qty') - _o.get('fee'), balance=0)

                                    self.order_list[currency][order_id]['timestamp'].append(_o.get('timestamp'))
                                    if self.order_list[currency][order_id]['remain_qty'] == 0:
                                        if _o.get('type') == 'SELL':
                                            self.balance['fiat'] += self.order_list[currency][order_id].get('fee')
                                        elif _o.get('type') == 'BUY':
                                            self.balance[currency]['balance'] -= self.order_list[currency][order_id].get('fee')

                                        pop_q.add(order_id)

                                    # Todo
                                    # 체결 정보 보내기.

                        for pop_i in pop_q:
                            self.order_list[currency].pop(pop_i)
                    else:
                        return 0

        ### Todo
        # 체크되지 않는 Order_id들 확인하기.


    def _send_order(self, order, _datetime=None):
        order_re = None
        update_type = "ORDER"

        if order.order_type == 'BUY':
            if self.balance['fiat'] - order.price * order.quantity < 0:
                return dict(result=False, msg='Bigger than fiat')
            elif order.quantity < MINUMUM_CURRENCY_QTY[order.currency]:
                return dict(result=False, msg='Lower than minimum quantity')
            else:
                order_re = self.api.order_buy(
                    currency=order.currency, fiat=self.fiat, price=order.price, quantity=order.quantity)
        elif order.order_type == 'SELL':
            if self.balance[order.currency]['avail'] - order.quantity < 0:
                return dict(result=False, msg='')
            elif order.quantity < MINUMUM_CURRENCY_QTY[order.currency]:
                return dict(result=False, msg='')
            else:
                order_re = self.api.order_sell(
                    currency=order.currency, fiat=self.fiat, price=order.price, quantity=order.quantity)
        else:
            return False

        if order_re.get('order_id'):

            # Todo
            # 2차
            # 1. Add Logger: Success Order
            # 2. Order를 전송하기 전에
            # 3. 어떤 가상화폐를 먼저 처리할 건지
            # 4. BUY 먼저 할지 SELL 먼저 할지
            # 5. order_result와 order가 일치하는지.

            order_id = order_re.get('order_id')
            sleep(0.04)
            stat_re = self.api.order_status(currency=order.currency, order_id=order_id)

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
                        use_balance=int(stat_re.get('qty') * stat_re.get('price')) - stat_re.get('fee'),
                        price=stat_re.get('price'), quantity=stat_re.get('qty'), order_type=order.order_type,
                        avail=-round(stat_re.get('qty'), R_OFF), balance=-round(stat_re.get('qty'), R_OFF))

                elif order.order_type == 'BUY':
                    self._update_quantity(
                        update_type=update_type, order_id=order_re.get('order_id'), currency=order.currency,
                        use_balance=-math.ceil(stat_re.get('price') * stat_re.get('qty')),
                        price=stat_re.get('price'), quantity=stat_re.get('qty'), order_type=order.order_type,
                        avail= stat_re.get('qty') - stat_re.get('fee'), balance=stat_re.get('qty') - stat_re.get('fee'))

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
                    'timestamp': [stat_re.get('timestamp')],
                    'remain_qty': stat_re.get('qty'),
                    'fee': round(stat_re.get('qty') * FEE_RATE, R_OFF) if order.order_type == 'BUY' else
                    math.ceil(int(stat_re.get('qty') * stat_re.get('price')) * FEE_RATE)
                }

                if order.order_type == 'SELL':
                    self._update_quantity(
                        update_type=update_type, order_id=order_re.get('order_id'), use_balance=0, currency=order.currency,
                        order_type=order.order_type, price=stat_re.get('price'), quantity=stat_re.get('qty'),
                        avail=-round(stat_re.get('qty'), R_OFF), balance=0)
                elif order.order_type == 'BUY':
                    self._update_quantity(
                        update_type=update_type, order_id=order_re.get('order_id'), currency=order.currency,
                        use_balance=-math.ceil(stat_re.get('price') * stat_re.get('qty')), order_type=order.order_type,
                        price=stat_re.get('price'), quantity=stat_re.get('qty'),
                        avail=0, balance=round(stat_re.get('qty') * (1 - FEE_RATE), R_OFF))
            else:
                return dict(result=False, msg="Failed Send Order")

            return dict(result=True, msg="Order Complete")

        else:
            return dict(result=False, msg="Failed Send Order")


    def send_orders(self):
        time_now = datetime.now()

        if self.orders.keys():
            pop_q = set()
            for order_t in self.orders.keys():
                if order_t < time_now:
                    pop_q.add(order_t)
                    for order in self.orders[order_t]:
                        self._send_order(order=order)
            for item in pop_q:
                self.orders.pop(item)
            pop_q.clear()


    def set_order(self, o, t=None):
        if isinstance(t, type(None)):
            return self._send_order(order=o, _datetime=datetime.now())
        else:
            self.orders[t].append(o)


    def _send_signal(self, signal_type, trade_type, currency, price, quantity, is_safety=False, error_message=None):
        eval_balance=int(price * quantity)
        profit= round((self.calc_estimated() - self.init_budget) / self.init_budget, 4) * 100
        data = dict(
            signal_type=signal_type,
            trade_type=trade_type,
            currency=currency,
            price=price,
            quantity=quantity,
            eval_balance=eval_balance,
            profit=profit,
            is_safety=is_safety,
            error_message=error_message
        )
        TradeApi.bot_signals(data)


    def _send_cancel(self, currency, order_id, qty=None):
        """
        ### order format
        self.order_list['{}'.format(order.currency)]['{}'.format(order_re.get('order_id'))] = {
                'currency': order.currency,
                'price': order.price,
                'quantity': order.quantuty,
                'order_type': order.order_type,
                'fiat': order.fiat
            }
        
        ### order status result
        {'info': {'currency': 'ZIL',
          'fee': '0',
          'feeRate': '0.001',
          'orderId': '84F42097-D4A7-4984-9F40-8C500CEAA848',
          'price': '24',
          'qty': '1.0000',
          'remainQty': '0.5000',
          'timestamp': '1547711535',
          'type': 'bid'},
         'status': 'live'}
         
         {'info': {'currency': 'ZIL',
          'fee': '0.00120000',
          'feeRate': '0.001',
          'orderId': 'D9776155-ED79-403B-B4DA-9F8E13C591FE',
          'price': '25.0',
          'qty': '1.2000',
          'remainQty': '0',
          'timestamp': '1547712831',
          'type': 'bid'},
         'status': 'filled'}
         
        """
        update_type = "CANCEL"
        cancel_result = False
        update_result = False
        
        # 주문 취소를 날리기 전에 해당 주문의 상태를 확인
        order_stat = self.api.order_status(currency=currency, order_id=order_id)
        
        # 해당 주문이 이미 취소된 경우
        # 주문이 없는 경우 order_cancel 요청 시 어떻게 반환되는지 확인 필요
        if order_stat == 'Order id is not exist':
            print("해당 order ID는 존재하지 않습니다.")
            return True
            
        order_c = self.order_list[currency][order_id]    
        
        # 해당 주문이 체결된 경우 balance update 
        # 얼마나 체결 됬는지 정보 필요 (order_list에 저장된 정보 quantity는 이전까지의 remain quantity)
        if order_stat['status'] == 'filled':
            # BUY 
            if order_c['order_type'] == 'BUY':
                update_result = self._update_quantity(
                    update_type=update_type, order_id=order_id, use_balance=0, currency=currency,
                    order_type=order_c['order_type'], price=order_c['price'], quantity=order_c['quantity'],
                    avail=round(order_c['remain_qty']*(1-FEE_RATE), R_OFF), balance=0)
                ### Todo
                # update_result 예외 처리
                
            # SELL
            elif order_c['order_type'] == 'SELL':
                use_balance = int(order_c['remain_qty']*order_c['price']) - math.ceil(int(order_c['remain_qty']*order_c['price'])*FEE_RATE)
                update_result = self._update_quantity(
                    update_type=update_type, order_id=order_id, use_balance=use_balance, currency=currency,
                    order_type=order_c['order_type'], price=order_c['price'], quantity=order_c['quantity'],
                    avail=0, balance=-round(order_c['remain_qty'], R_OFF))
                
                ### Todo
                # update_result 예외 처리
            
            return True
        
        
        # 해당 주문이 미체결 상태인 경우
        elif order_stat['status'] == 'live':
            # 입력 받은 quantity가 없는 경우 remain quantity 이용
            if qty is None:
                quantity_c = truncate(float(order_stat['info']['remainQty']), 4)
                
            # 입력 받은 quantity만큼 부분취소
            else:
                if qty < float(order_stat['info']['remainQty']):
                    quantity_c = truncate(qty, 4)
                ### Todo
                # 입력 받은 quantity가 remainQty 보다 많은 경우
                else:
                    quantity_c = truncate(float(order_stat['info']['remainQty']), 4)
            
            # 주문 취소 api 요청
            cancel_result = self.api.order_cancel(currency=currency, order_id=order_id, order_type=order_c['order_type'],
                                                  fiat='krw', price=order_c['price'], quantity=quantity_c)
            
            # 주문 취소에 성공한 경우 balance update
            if cancel_result['result'] == 'success':
                
                # update balance
                # BUY
                if order_c['order_type'] == 'BUY':
                    price = int(order_stat['info']['price'])
                    use_balance = math.ceil(quantity_c * price)
                    update_result = self._update_quantity(
                        update_type=update_type, order_id=order_id, use_balance=use_balance, currency=currency,
                        order_type=order_c['order_type'], price=order_c['price'], quantity=order_c['quantity'],
                        avail=0, balance=-round(quantity_c * (1-FEE_RATE), R_OFF))
                    
                    ### Todo
                    # update_result 예외 처리
                    
                # SELL
                elif order_c['order_type'] == 'SELL':
                    update_result = self._update_quantity(
                        update_type=update_type, order_id=order_id, use_balance=0, currency=currency,
                        order_type=order_c['order_type'], price=order_c['price'], quantity=order_c['quantity'],
                        avail=round(quantity_c, R_OFF), balance=0)
                    
                    ### Todo
                    # update_result 예외 처리
                
                # 전체가 취소된 경우 (list에서 pop)
                if qty is None or qty >= float(order_stat['info']['remainQty']):
                    return True
                # 부분취소인 경우 False를 반환 (list에서 pop하지 않도록)
                elif qty < float(order_stat['info']['remainQty']):
                    self.order_list[currency][order_id]['remain_qty'] -= qty
                    return False
                
            # 주문 취소에 실패한 경우 result로 어떻게 반환되는지 확인 필요
            else:
                ### Todo
                # 주문 취소에 실패하는 경우 case 나누어서 처리 필요
                # 1. 주문 취소 시 전체 또는 부분 체결이 된 경우
                # 2. 주문 취소 시 사용자가 취소를 한 경우
                
                # 다시 status를 조회하여 확인 필요
                return False
        

    def set_cancel(self, currency=None, order_id=None, qty=None):
        if qty is None:
            # 입력 받은 quantity가 없는 경우
            if order_id is None and currency is None:
                # 현재 주문 전체 취소
                print("cancel #1")
                
                for _currency in self.currencies:
                    if self.order_list[_currency].keys():
                        pop_q = set()
                        print(self.order_list[_currency])
                        for _order_id in self.order_list[_currency].keys():
                            if self._send_cancel(currency=_currency, order_id=_order_id):
                                pop_q.add(_order_id)
                                
                        for item in pop_q:
                            self.order_list[_currency].pop(item)
                            print("{} 주문이 취소 되었습니다.")
                    else:
                        print('해당 거래소에 {}에 대한 주문이 없습니다.'.format(_currency))
                        continue
                            
            elif order_id is None:
                # 특정 currency의 주문 전체 취소
                print("cancel #2")
                      
                if self.order_list[currency].keys():
                    pop_q = set()
                    print(self.order_list[currency])
                    for _order_id in self.order_list[currency].keys():
                        if self._send_cancel(currency=currency, order_id=_order_id):
                            pop_q.add(_order_id)
                                
                    for item in pop_q:
                        self.order_list[currency].pop(item)
                      
                else:
                    print("입력하신 {}에 대한 주문이 없습니다.".format(currency))

            elif order_id is not None and currency is None:
                print("currency를 함께 입력해야 합니다.")
                
            else:
                # 특정 order_id의 주문 취소
                print("cancel #3")
                
                if order_id in self.order_list[currency].keys():
                    if self._send_cancel(currency=currency, order_id=order_id):
                        self.order_list[currency].pop(order_id)
                        
                else:
                    print("입력하신 order ID가 존재하지 않습니다.")
                        
        # 입력 받은 quantity만큼 부분 취소
        else:
            qty = truncate(qty, 4)
            
            if currency is None or order_id is None:
                print("currency와 order ID를 함께 입력해야 합니다.")
                
            else:
                print("cancel #4")
                
                if order_id in self.order_list[currency].keys():
                    if self._send_cancel(currency=currency, order_id=order_id, qty=qty):
                        self.order_list[currency].pop(order_id)
                
                else:
                    print("입력하신 order ID가 존재하지 않습니다.")
            

    def get_balance(self):
        return self.balance


    def get_order_list(self):
        self.update_balance()
        return self.order_list


    def get_orders(self):
        return self.orders


    def _update_quantity(self, update_type, order_id, currency, price, quantity,
                         order_type, use_balance, avail, balance):
        self.balance['fiat'] += use_balance
        self.balance[currency]['avail'] += avail
        self.balance[currency]['balance'] += balance
        self._round_off_balance()
        print(f'[{datetime.now()} {update_type}], order_id: {order_id}, Currency: {currency}, '
              f'OrderType: {order_type}, Fiat: {use_balance}, Avail: {avail}, Balance: {balance}')
        print(f'MY BALANCE: {self.balance}')
        if self.running_mode == 'LIVE':
            data = {
                'use_balance': use_balance,
                'exchange': self.name,
                'fiat': self.fiat,
                'currency': currency,
                'avail': avail,
                'balance': balance
            }
            TradeApi.bot_quantity(data=data)
            self._send_signal(
                signal_type=update_type, trade_type=order_type, currency=currency, price=price, quantity=quantity
            )

            return True

        else:
            return True


    def get_time(self):
        return datetime.now()
    
    
    def _round_off_balance(self):
        for currency in self.currencies:
            self.balance[currency]['avail'] = round(self.balance[currency]['avail'], R_OFF)
            self.balance[currency]['balance'] = round(self.balance[currency]['balance'], R_OFF)


    def calc_estimated(self):
        estimated = 0
        _balance = deepcopy(self.balance)

        if self.order_list.keys():
            for order in self.order_list.keys():
                order_c = self.order_list[order]

                if order_c.get('order_type') == 'BUY':
                    estimated += math.ceil(order_c['price'] * order_c['quantity'])
                    _balance[order_c['currency']]['balance'] -= order_c['quantity']

        for k in _balance.keys():
            if k == 'fiat':
                estimated += _balance[k]
            else:
                sleep(0.035)
                current_orderbook = self.api.get_orderbook(currency=k, fiat=self.fiat, limit=30)
                estimated += _balance[k]['balance'] * current_orderbook['bids'][0].get('price')

        return estimated


    def clear_balance(self):
        for k in self.balance.keys():
            if k == 'fiat':
                continue
            else:
                price = self.api.get_orderbook(currency=k, fiat=self.fiat, limit=30)['bids'][0]['price']
                self._send_order(
                    Order(
                        currency=k, order_type='SELL', fiat=self.fiat, price=price,
                        quantity=self.balance[k]['balance'], is_safety=True)
                )


class CoinoneBacktest(BaseExchange):
    name = NAME
    fee_rate = FEE_RATE

    def __init__(self, start_date, end_date, init_budget, currency_list, interval_list, fiat, slippage_rate=None,
                 use_data="LIVE", data_path='data'):
        super().__init__(init_budget=init_budget, currency_list=currency_list, interval_list=interval_list, fiat=fiat)
        if slippage_rate is None:
            self.slippage_rate = SLIPPAGE_RATE
        else:
            self.slippage_rate = slippage_rate

        self.start_date = start_date
        self.end_date= end_date
        self.use_data = use_data
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
        self.data_path = data_path


    def init_dataframe(self):

        forward_candle_frame = {
            1: 1440,
            3: 480,
            5: 288,
            15: 120,
            30: 120,
            60: 120,
            120: 150,
            240: 150,
            1440: 180
        }
        from_date = {}

        for interval in self.intervals:
            from_date[interval] = self.start_date - timedelta(minutes=interval * forward_candle_frame[interval])

        if self.use_data == 'LOCAL':
            path = f'{self.data_path}/{NAME}'
            files = os.listdir(path)

        for currency in self.currencies:
            for interval in self.intervals:
                if self.use_data == 'LIVE':
                    df = CandleApi.get_df(
                        exchange=NAME, currency=currency, fiat=self.fiat, interval=interval,
                        from_date=from_date[interval], until_date=self.end_date)
                    df['datetime'] = [datetime.fromtimestamp(t) for t in df['timestamp']]
                    df.set_index(keys='datetime', inplace=True)
                    self.data[f'{currency}_{interval}'] = df

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
                        [datetime.fromtimestamp(t) for t in self.data[f'{currency}_{interval}']['timestamp']]
                    self.data[f'{currency}_{interval}'].set_index(keys='datetime', inplace=True)
                    del(df)

                self.updated_len[f'{currency}_{interval}'] = len(self.data[f'{currency}_{interval}'])


    def init_test_dataframe(self):
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
                        if not result.get('result'):
                            print("Order Fail MSG: {}".format(result.get('msg')))
                        pop_q.add(order_t)

        for i in pop_q:
            self.orders.pop(i)

        pop_q.clear()

        if self.order_list.keys():
            estimated, earning_rate = self._get_earning_rate()
            for k in self.order_list.keys():
                self.estimated_list.append({'date': k, 'estimated': round(estimated, 4)})
                self.trade_history[k] = {
                    'order_list': self.order_list[k],
                    'balance': deepcopy(self.balance),
                    'estimated': estimated,
                    'earning_rate': earning_rate
                }

                pop_q.add(k)

            self.max_profit = earning_rate if earning_rate > self.max_profit else self.max_profit
            self.max_loss = earning_rate if earning_rate < self.max_loss else self.max_loss

        for i in pop_q:
            self.order_list.pop(i)

        return True


    def _send_order(self, order, _datetime=None):
        if order.quantity < MINUMUM_CURRENCY_QTY[order.currency]:
            return dict(result=False, msg='Lower than minimum quantity')
        else:
            if order.order_type == 'BUY':
                if order.price * order.quantity <= self.balance['fiat']:
                    self.balance['fiat'] -= order.price * order.quantity
                    self.balance[order.currency]['avail'] += order.quantity * (1 - (FEE_RATE + self.slippage_rate))
                    self.balance[order.currency]['balance'] += order.quantity * (1 - (FEE_RATE + self.slippage_rate))
                else:
                    return dict(result=False, msg='Not enough Fiat.')
            elif order.order_type == 'SELL':
                if order.quantity <= self.balance[order.currency]['balance']:
                    self.balance['fiat'] += order.price * order.quantity * (1 - (FEE_RATE + self.slippage_rate))
                    self.balance[order.currency]['avail'] -= order.quantity
                    self.balance[order.currency]['balance'] -= order.quantity
                else:
                    return dict(result=False, msg='Not enough coin balance.')
            else:
                return dict(result=False, msg='Unkown OrderType')

            self.total_fee += order.price * order.quantity * FEE_RATE
            self.total_slippage += order.price * order.quantity * self.slippage_rate
            self.order_list[self._get_df_datetime() if _datetime is None else _datetime].append(order)
            return dict(result=True, msg='Send order complete')


    def set_order(self, o, t=None):
        if isinstance(t, type(None)):
            return self._send_order(o)
        else:
            self.orders[t].append(o)
        return dict(result=True, msg='Add Order Complete')

    def set_cancel(self, currency=None, order_id=None, qty=None):
        return False


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
            self.data['{}_{}'.format(currency, self.intervals[0])]['timestamp'].iloc[-1])

        if len(self.intervals) > 1:
            for interval in self.intervals[1:]:
                df_datetime = datetime.fromtimestamp(
                    self.data['{}_{}'.format(currency, interval)]['timestamp'].iloc[-1])
                if df_datetime > datetime_dump:
                    datetime_dump = df_datetime

        return datetime_dump


    def _get_earning_rate(self):
        estimated = 0.0

        for key in self.balance.keys():
            if key == 'fiat':
                estimated += self.balance[key]
            elif self.balance[key]['balance'] is not 0 or 0.0:
                estimated += self.balance[key]['balance'] * self._get_currency_price(currency=key)

        earning_rate = round((estimated - self.init_budget) / self.init_budget, 4)

        return estimated, earning_rate


    def _get_currency_price(self, currency):
        datetime_dump = datetime.fromtimestamp((self.data['{}_{}'.format(
            currency, self.intervals[0])]['timestamp'].iloc[-1]))
        recently_df = "{}_{}".format(currency, self.intervals[0])

        if len(self.intervals) > 1:
            for interval in self.intervals:
                df_datetime = datetime.fromtimestamp(self.data['{}_{}'.format(
                    currency, interval)]['timestamp'].iloc[-1])
                if df_datetime > datetime_dump:
                    datetime_dump = df_datetime
                    recently_df = "{}_{}".format(currency, interval)
        return self.data[recently_df]['close'].iloc[-1]


