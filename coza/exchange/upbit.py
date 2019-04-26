from .base_exchange import TradeBase, BacktestBase
from datetime import datetime, timedelta
from coza.api.exchange import UpbitAPI
from coza.api import TradeApi, ExchangeApi, CandleApi
from coza.errors import InputValueValidException
from coza.objects import Order
from coza.utils import truncate, now, KST
from coza.logger import logger
from copy import deepcopy
from collections import defaultdict
from time import sleep

import pandas as pd
import os


NAME = 'upbit'
MINIMUM_TRADE_PRICE = {'btc': 1000}
INTERVAL_LIST = {1, 3, 5, 15, 30, 60, 240}
FIAT = {'KRW', 'BTC', 'ETH', 'USDT'}
FEE_RATE = 0.0005
SLIPPAGE_RATE = 0.002
R_OFF = 8


class UpbitTrade(TradeBase):
    def __init__(self, api_key, secret_key, init_budget, currency_list, interval_list, fiat,
                 running_mode='LIVE', using_api='EXCHANGE'):

        self.api_key = api_key
        self.secret_key = secret_key
        self.running_mode = running_mode
        self.using_api = using_api

        super().__init__(name=NAME, init_budget=init_budget, currency_list=currency_list, interval_list=interval_list,
                         tz=KST, r_off=R_OFF, fiat=fiat)
        self.init_balance()
        self.data = dict()
        self.orders = defaultdict(list)
        self.uptime = 0.0
        self.delay_time = 0.0
        self.order_list = {f'{currency}': dict() for currency in currency_list}
        self.api = UpbitAPI(api_key=self.api_key, secret_key=self.secret_key)

        try:
            markets = self.api.get_markets()
            self.market_table = {f'{currency}': {'id': f'{self.fiat.upper()}-{currency.upper()}'} for currency in currency_list}
            for currency in self.market_table.keys():
                if self.market_table[currency]['id'] in list(markets[self.fiat.upper()]['market']):
                    order_chance = self.api.get_order_chance(market_id=self.market_table[currency]['id'])
                    self.market_table[currency]['ask_fee'] = float(order_chance.get('ask_fee'))
                    self.market_table[currency]['bid_fee'] = float(order_chance.get('bid_fee'))
                    logger.info('ask_fee of {} : {}'.format(currency, self.market_table[currency]['ask_fee']))
                    logger.info('bid_fee if {} : {}'.format(currency, self.market_table[currency]['bid_fee']))
                else:
                    # Todo
                    # Raise Exception Input Value Validation
                    pass
        except Exception as e:
            logger.critical(msg=e)
            self.exit(msg=e, stop_bot=True)


    def update_balance(self):
        update_type = "FILLED"

        for currency in self.order_list.keys():
            if self.order_list[currency].keys():
                try:
                    if self.using_api == 'EXCHANGE':
                        c_order = self.api.get_order_list(market_id=self.market_table[currency]['id'], state='done', order_by='desc')
                    elif self.using_api == 'CATSLAB':
                        c_order = TradeApi.order_list(
                            {
                                'market_id':self.market_table[currency]['id'],
                                'state':'done',
                                'page': 1,
                                'order_by':'desc'
                            })

                except Exception as e:
                    logger.critical(msg=e)
                    self.exit(msg=e, stop_bot=True)

                if not c_order.get('error'):
                    pop_q = set()
                    for order_id in self.order_list[currency].keys():
                        if order_id in c_order.keys():
                            order_ = self.order_list[currency][order_id]
                            if order_['order_type'] == 'BUY':
                                self._update_quantity(
                                    update_type=update_type, order_id=order_id, currency=currency,
                                    order_type=order_['order_type'], price=order_['price'],
                                    quantity=order_['remain_qty'], use_balance=0, avail=order_['remain_qty'], balance=0)
                            elif order_['order_type'] == 'SELL':
                                use_balance = round((order_['price']*order_['remain_qty'])*(1-self.market_table[currency]['ask_fee']), R_OFF)
                                self._update_quantity(
                                    update_type=update_type, order_id=order_id, currency=currency,
                                    order_type=order_['order_type'], price=order_['price'],
                                    quantity=order_['remain_qty'], use_balance=use_balance,
                                    avail=0, balance=-round(order_['remain_qty'], R_OFF))
                            else:
                                # Raise Exception.
                                pass
                            pop_q.add(order_id)
                        else:
                            if self.using_api == 'EXCHANGE':
                                order_stat = self.api.get_order_stat(order_id=order_id)
                            elif self.using_api == 'CATSLAB':
                                order_stat = TradeApi.order_status({'order_id':order_id})
                            try:
                                if order_stat.get('state') == 'wait' and len(order_stat.get('trades')) != 0:
                                    update_id = False
                                    for trade in order_stat.get('trades'):
                                        if order_['last_trade_id'] == trade['uuid']:
                                            break
                                        if trade['side'] == 'bid':
                                            self._update_quantity(
                                                update_type=update_type, order_id=order_id, currency=currency,
                                                order_type='BUY', price=float(trade['price']), quantity=float(trade['volume']),
                                                use_balance=0, avail=float(trade['volume']), balance=0)
                                        elif trade['side'] == 'ask':
                                            use_balance = round(float(trade['funds'])*(1-self.market_table[currency]['ask_fee']), R_OFF)
                                            self._update_quantity(
                                                update_type=update_type, order_id=order_id, currency=currency,
                                                order_type='SELL', price=float(trade['price']), quantuty=float(trade['volume']),
                                                use_balance=use_balance, avail=0, balance=-float(trade['volume']))
                                        else:
                                            #
                                            pass
                                        update_id = True

                                    if update_id:
                                        self.order_list[currency][order_id]['last_trade_id'] = order_stat.get('trades')[0]
                                elif order_stat.get('state') == 'cancel':
                                    # Todo
                                    # Cancel된 Order 반영.
                                    
                                    
                                    pass
                            except:
                                # Raise Exception
                                pass

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
            elif order.quantity * order.price < MINIMUM_TRADE_PRICE.get(order.currency, 500):
                logger.debug(f'[ORDER_FAILED] Failed to send order because of \'Minimum Trade Price\' : {order}')
                return dict(error='Minimum order price is 500 KRW')
        elif order.order_type == 'SELL':
            if self.balance[order.currency]['avail'] - order.quantity < 0:
                logger.debug(f'[ORDER_FAILED] Failed to send order because of \'Lack of Balance\' : {order}')
                return dict(error='Lack of Balance')
            elif order.quantity * order.price < MINIMUM_TRADE_PRICE.get(order.currency, 500):
                logger.debug(f'[ORDER_FAILED] Failed to send order because of \'Minimum Trade Price\' : {order}')
                return dict(error='Minimum order price is 500 KRW')
        else:
            return False

        try:
            if self.using_api == 'EXCHANGE':
                order_re = self.api.get_order(
                    market_id=self.market_table[order.currency]['id'],
                    side='bid' if order.order_type == 'BUY' else 'ask',
                    volume=order.quantity,
                    price=order.price,
                )
            elif self.using_api == 'CATSLAB':
                order_re = TradeApi.order(
                    {
                        'market_id':self.market_table[order.currency]['id'],
                        'side':'bid' if order.order_type == 'BUY' else 'ask',
                        'volume': order.quantity,
                        'price': order.price,
                        'ord_type': 'limit'
                    })

            if order_re.get('uuid'):
                logger.debug(f'[ORDER] Successfully sended order : {order}')
                # Todo
                # 2차
                # 1. Add Logger: Success Order
                # 2. Order를 전송하기 전에
                # 3. 어떤 가상화폐를 먼저 처리할 건지
                # 4. BUY 먼저 할지 SELL 먼저 할지
                # 5. order_result와 order가 일치하는지.

                order_id = order_re.get('uuid')
                sleep(0.04)
                if self.using_api == 'EXCHANGE':
                    stat_re = self.api.get_order_stat(order_id=order_id)
                elif self.using_api == 'CATSLAB':
                    stat_re = TradeApi.order_status({'order_id':order_id})

                if stat_re.get('state') == 'done':
                    update_type = 'ORDER_FILLED'

                    if order.order_type == 'SELL':
                        use_balance = round(float(stat_re.get('volume'))*float(stat_re.get('price')) - float(stat_re.get('paid_fee')), R_OFF)
                        self._update_quantity(
                            update_type=update_type, order_id=order_id, currency=order.currency, use_balance=use_balance,
                            price=float(stat_re.get('price')), quantity=float(stat_re.get('volume')), order_type=order.order_type,
                            avail=-round(float(stat_re.get('volume')), R_OFF), balance=-round(float(stat_re.get('volume')), R_OFF))

                    elif order.order_type == 'BUY':
                        use_balance = round(float(stat_re.get('volume')) * float(stat_re.get('price')) + float(stat_re.get('paid_fee')), R_OFF)
                        self._update_quantity(
                            update_type=update_type, order_id=order_id, currency=order.currency, use_balance=-use_balance, price=float(stat_re.get('price')),
                            quantity=float(stat_re.get('volume')), order_type=order.order_type,
                            avail=round(float(stat_re.get('volume')), R_OFF), balance=round(float(stat_re.get('volume')), R_OFF))

                elif stat_re.get('state', None) == 'wait':
                    self.order_list[f'{order.currency}'][f'{order_id}'] = {
                        'currency': order.currency,
                        'price': float(stat_re.get('price')),
                        'quantity': float(stat_re.get('volume')),
                        'order_type': order.order_type,
                        'fiat': self.fiat,
                        'datetime': datetime.strptime(stat_re.get('created_at')[:19], '%Y-%m-%dT%H:%M:%S'),
                        'last_trade_id': None,
                        'remain_qty': float(stat_re.get('remaining_volume')),
                        'locked': float(stat_re.get('locked')),
                        'fee': float(stat_re.get('paid_fee'))
                    }

                    if order.order_type == 'SELL':
                        self._update_quantity(
                            update_type=update_type, order_id=order_re.get('uuid'), use_balance=0, currency=order.currency,
                            order_type=order.order_type, price=float(stat_re.get('price')), quantity=float(stat_re.get('volume')),
                            avail=-round(float(stat_re.get('volume')), R_OFF), balance=0)
                    elif order.order_type == 'BUY':
                        use_balance = round(float(stat_re.get('price')) * float(stat_re.get('volume')) * (1 + self.market_table[order.currency]['bid_fee']), R_OFF)
                        self._update_quantity(
                            update_type=update_type, order_id=order_re.get('uuid'), currency=order.currency,
                            use_balance=-use_balance, order_type=order.order_type,
                            price=float(stat_re.get('price')), quantity=float(stat_re.get('volume')),
                            avail=0, balance=round(float(stat_re.get('volume')), R_OFF))
                else:
                    logger.debug(f'[ORDER_FAILED] Failed to send order : {order}')
                    return dict(error="Failed To Send Order")

                return dict(error="Order Completed")

            elif order_re.get('error'):
                logger.info(f'[ORDER_FAILDE] Failed to send order : {order}')
                return dict(error=order_re.get('error'))

            else:
                logger.debug(f'[ORDER_FAILED] Failed to send order : {order}')
                logger.info(f'order_re : {order_re}')
                return dict(error="Failed To Send Order")
        except Exception as e:
            logger.error(msg=e)
            self.exit(msg=e)


    def _send_cancel(self, currency, order_id, qty=None):
        cancel_result = False
        update_result = False
        
        if self.using_api == 'CATSLAB':
            try:
                order_stat = TradeApi.order_status({'order_id': order_id})
            except Exception as e:
                logger.error(msg=e)
                self._send_error(msg=e)
        elif self.using_api == 'EXCHANGE':
            try:
                order_stat = self.api.get_order_stat(order_id=order_id)
            except Exception as e:
                logger.error(msg=e)
                self._send_error(msg=e)

        if order_stat.get('error', None) is not None:
            logger.debug('[CANCEL_FAILED] 해당 order_id는 존재하지 않습니다.')
            return True
        
        order_c = self.order_list[currency][order_id]
        remainQty = truncate(round(float(order_stat.get('remaining_volume')), R_OFF), 4)
        
        if order_stat.get('state') == 'done':
            logger.debug(f'[ORDER_FILLED] Already filled order {order_id} : {self.order_list[currency][order_id]}')
            
            update_type = "FILLED"
            if order_c['order_type'] == 'BUY':
                self._update_quantity(
                    update_type=update_type, order_id=order_id, use_balance=0, currency=currency,
                    order_type=order_c['order_type'], price=order_c['price'], quantity=order_c['remain_qty'],
                    avail=round(order_c['remain_qty'], R_OFF), balance=0)
            elif order_c['order_type'] == 'SELL':
                use_balance = round((order_c['remain_qty']*order_c['price'])*(1-self.market_table[currency]['ask_fee']), R_OFF)
                self._update_quantity(
                    update_type=update_type, order_id=order_id, use_balance=use_balance, currency=currency,
                    order_type=order_c['order_type'], price=order_c['price'], quantity=order_c['remain_qty'],
                    avail=0, balance=-round(order_c['remain_qty'], R_OFF))

            return True
        
        elif order_stat.get('state') == 'wait':
            logger.debug(f'[ORDER_LIVE] Still live order {order_id} : {order_c}')
            ### Todo 
            # TEST
            partial_qty = round(order_c['remain_qty'] - remainQty, R_OFF)
            if abs(partial_qty) >= 0.0001:
                logger.debug(f'[ORDER_FILLED_PARTIALLY] : {partial_qty}')
                
                update_type = "FILLED"
                if order_c['order_type'] == 'BUY':
                    self._update_quantity(
                        update_type=update_type, order_id=order_id, use_balance=0, currency=currency,
                        order_type=order_c['order_type'], price=order_c['price'], quantity=partial_qty,
                        avail=partial_qty, balance=0)
                elif order_c['order_type'] == 'SELL':
                    use_balance = round((partial_qty*order_c['price'])*(1-self.market_table[currency]['ask_fee']), R_OFF)
                    self._update_quantity(
                        update_type=update_type, order_id=order_id, use_balance=use_balance, currency=currency,
                        order_type=order_c['order_type'], price=order_c['price'], quantity=partial_qty,
                        avail=0, balance=-partial_qty)
                
            if self.using_api == 'CATSLAB':
                try:
                    cancel_result = TradeApi.order_cancel({'order_id':order_id})
                except Exception as e:
                    logger.error(msg=e)
                    self._send_error(msg=e)
            elif self.using_api == 'EXCHANGE':
                try:
                    cancel_result = self.api.get_cancel(order_id=order_id)
                except Exception as e:
                    logger.error(msg=e)
                    self._send_error(msg=e)
            
            if cancel_result.get('uuid') == order_id:
                logger.debug(f'[ORDER_CANCELED] Successfully canceled order : {order_c}')
                logger.info(f'Canceled quantity : {remainQty}')
                update_type = "CANCEL"
                if order_c['order_type'] == 'BUY':
                    use_balance = round((remainQty * order_c['price'])*(1+self.market_table[currency]['bid_fee']), R_OFF)
                    self._update_quantity(
                        update_type=update_type, order_id=order_id, use_balance=use_balance, currency=currency,
                        order_type=order_c['order_type'], price=order_c['price'], quantity=remainQty,
                        avail=0, balance=-round(remainQty, R_OFF))
                elif order_c['order_type'] == 'SELL':
                    self._update_quantity(
                        update_type=update_type, order_id=order_id, use_balance=0, currency=currency,
                        order_type=order_c['order_type'], price=order_c['price'], quantity=remainQty,
                        avail=round(remainQty, R_OFF), balance=0)
                    
                return True
            
            elif cancel_result.get('error', None) is not None:
                logger.debug(f'[ORDER_CANCEL_FAILED] Failed to cancel order {order_id} : {order_c}')
                return False
        else:
            logger.debug(f'[ORDER_CANCEL_FAILED] Failed to cancel order {order_id} : {order_c}')
            return False
        

    def set_cancel(self, currency=None, order_id=None, qty=None):
        if order_id is None and currency is None:
            logger.debug('Canceling all orders which are not filled...')

            for _currency in self.currencies:
                if self.order_list[_currency].keys():
                    logger.info(f'order_list to cancel : {self.order_list[_currency]}')
                    pop_q = set()
                    for _order_id in self.order_list[_currency].keys():
                        logger.debug(f'Canceling order {_order_id} : {self.order_list[_currency][_order_id]}')
                        try:
                            if self._send_cancel(currency=_currency, order_id=_order_id):
                                pop_q.add(_order_id)
                        except Exception as e:
                            logger.error(msg=e)
                            self._send_error(msg=e)

                    for item in pop_q:
                        self.order_list[_currency].pop(item)

        elif order_id is None:
            logger.debug(f'Canceling all orders of {currency}...')
            logger.info(f'order_list to cancel : {self.order_list[currency]}')

            if self.order_list[currency].keys():
                pop_q = set()
                for _order_id in self.order_list[currency].keys():
                    logger.info(f'Canceling order {_order_id} : {self.order_list[currency][_order_id]}')
                    try:
                        if self._send_cancel(currency=currency, order_id=_order_id):
                            pop_q.add(_order_id)
                    except Exception as e:
                        logger.error(msg=e)
                        self._send_error(msg=e)

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
                try:
                    if self._send_cancel(currency=currency, order_id=order_id):
                        self.order_list[currency].pop(order_id)
                except Exception as e:
                    logger.error(msg=e)
                    self._send_error(msg=e)
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
                        price = self.api.get_orderbook(market_id=self.market_table[k]['id'])['orderbook']['bid_price'][0]
                    elif self.using_api == 'CATSLAB':
                        price = ExchangeApi.get_orderbook(exchange=NAME, currency=k)['orderbook']['bid_price'][0]
                    self._send_order(
                        Order(
                            currency=k, order_type='SELL', fiat=self.fiat, price=price, quantity=self.balance[k]['balance'])
                    )
                except Exception as e:
                    logger.critical(msg=e)
                    self._send_error(msg=e)


    def get_orderbook(self, currency):
        try:
            if self.using_api == 'CATSLAB':
                orderbook = pd.DataFrame(ExchangeApi.get_orderbook(exchange=NAME, currency=currency)['orderbook'])
            elif self.using_api == 'EXCHANGE':
                orderbook = self.api.get_orderbook(market_id=self.market_table[currency]['id'])['orderbook']
        except Exception as e:
            logger.error(msg=e)
            self._send_error(msg=e)
            return dict(error=e)

        return orderbook


class UpbitBacktest(BacktestBase):

    def __init__(self, start_date, end_date, init_budget, currency_list, interval_list, fiat, slippage_rate=None,
                 use_data='LIVE', data_path='data'):

        self.name = NAME
        self.fee_rate = FEE_RATE

        if slippage_rate is None:
            self.slippage_rate = SLIPPAGE_RATE
        elif isinstance(slippage_rate, float):
            self.slippage_rate = SLIPPAGE_RATE
        else:
            pass

        self.start_date = start_date.astimezone(KST)
        self.end_date = end_date.astimezone(KST)
        self.use_data = use_data
        self.data_path = data_path

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
            60: 120,
            240: 150
        }
        from_date = {}
        until_date = {}

        for interval in self.intervals:
            from_date[interval] = self.start_date - timedelta(minutes=interval * forward_candle_frame[interval])
            until_date[interval] = self.end_date - timedelta(minutes=interval)

        if self.use_data == 'LOCAL':
            path = f'{self.data_path}/{NAME}'
            files = os.listdir(path)

        for currency in self.currencies:
            for interval in self.intervals:
                if self.use_data == 'LIVE':
                    df = CandleApi.get_df(
                        exchange=NAME, currency=currency, fiat=self.fiat, interval=interval,
                        from_date=from_date[interval], until_date=until_date[interval])
                    df['datetime'] = [datetime.fromtimestamp(t).astimezone(KST) for t in df['timestamp']]
                    df.set_index(keys='datetime', inplace=True)
                    self.data[f'{currency}_{interval}'] = df

                elif self.use_data == 'LOCAL':
                    filename = f'{currency}_{interval}_{self.fiat}.csv'
                    try:
                        df = pd.read_csv(os.path.join(path, filename)).sort_values(by=['timestamp'])
                    except FileNotFoundError:
                        print(f"{filename} 파일이 존재하지 않습니다.")

                    try:
                        self.data[f'{currency}_{interval}'] = \
                            df[df[df['timestamp'] >= datetime.timestamp(from_date[interval])].index[0]:
                               df[df['timestamp'] <= datetime.timestamp(self.end_date)].index[-1]]
                        self.data[f'{currency}_{interval}']['datetime'] = \
                            [datetime.fromtimestamp(t).astimezone(KST) for t in
                             self.data[f'{currency}_{interval}']['timestamp']]
                    except Exception as e:
                        logger.critical(msg=e)
                        self.exit(msg=e, stop_bot=True)
                    self.data[f'{currency}_{interval}'].set_index(keys='datetime', inplace=True)
                    del (df)

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
            self.data[curr_inter] = self.test_df[curr_inter][:self.start_date - timedelta(minutes=2 * interval)]

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
            fiat = self.init_budget
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

            self.max_profit = estimated_dict.get('earning_rate') if estimated_dict.get(
                'earning_rate') > self.max_profit else self.max_profit
            self.max_loss = estimated_dict.get('earning_rate') if estimated_dict.get(
                'earning_rate') < self.max_loss else self.max_loss

        for i in pop_q:
            self.order_list.pop(i)

        return True


    def _send_order(self, order, _datetime=None):
        if order.price * order.quantity < MINIMUM_TRADE_PRICE:
            logger.debug(f'[ORDER_FAILED] Failed to send order because of \'Minimum Trade Price\' : {order}')
            return dict(error='Lower than minimum trade price')
        else:
            if order.order_type == 'BUY':
                if round(order.price * order.quantity * (1 + self.fee_rate), R_OFF) <= self.balance['fiat']:
                    self.balance['fiat'] -= round(order.price * order.quantity * (1 + self.fee_rate + self.slippage_rate), R_OFF)
                    self.balance[order.currency]['avail'] += round(order.quantity, R_OFF)
                    self.balance[order.currency]['balance'] += round(order.quantity, R_OFF)
                else:
                    logger.debug(f'[ORDER_FAILED] Failed to send order because of \'Lack of Balance\' : {order}')
                    return dict(error='Not enough Fiat.')
            elif order.order_type == 'SELL':
                if order.quantity <= self.balance[order.currency]['balance']:
                    self.balance['fiat'] += round(order.price * order.quantity * (1 - (self.fee_rate + self.slippage_rate)), R_OFF)
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
        c_func = 'set_order'
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
                currency_estimated += round(self.balance[key]['balance'] * self._get_currency_price(currency=key),
                                            R_OFF)

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


    def get_order_quantity(self, price, volume=1.0):
        if volume > 1 or not isinstance(volume, float):
            return False

        balance = deepcopy(self.balance['fiat'])
        balance / (price * (1 + self.fee_rate + self.slippage_rate))
