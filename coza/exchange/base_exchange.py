from abc import ABC, abstractmethod
from coza.api import TradeApi, CandleApi
from coza.utils import now
from coza.objects import Order
from coza.errors import InputValueValidException
from coza.logger import logger
from datetime import datetime, timedelta
from collections import defaultdict
from time import sleep

import numpy as np
import sys


class TradeBase(ABC):
    def __init__(self, name, init_budget, currency_list, interval_list, tz, r_off, fiat=None):
        self.name=name
        self.fiat=fiat
        self.tz = tz
        self.r_off = r_off
        self.updated_len = dict()
        self.is_update = dict()
        self.init_budget = init_budget
        self.currencies = tuple(currency_list)
        self.intervals = tuple(interval_list)

    def init_dataframe(self):
        logger.debug('Initializing dataframe...')

        time_now = now(exchange=self.name, rounding_seconds=True)
        until_date = {interval: time_now - timedelta(minutes=interval) for interval in self.intervals}

        for currency in self.currencies:
            for interval in self.intervals:
                try:
                    df = CandleApi.get_df(
                        exchange=self.name, currency=currency, fiat=self.fiat, interval=interval, until_date=until_date[interval]
                    )
                except Exception as e:
                    self.exit(msg=e,stop_bot=True)

                if df is not None:
                    df['datetime'] = [datetime.fromtimestamp(t).astimezone(self.tz) for t in df['timestamp']]
                    df.set_index(keys='datetime', inplace=True)
                    self.data[f'{currency}_{interval}'] = df
                    self.is_update[f'{currency}_{interval}'] = False
                    self.updated_len[f'{currency}_{interval}'] = len(self.data[f'{currency}_{interval}'])

                    logger.debug(f'Prepared Candle data {currency}_{interval}')
                    logger.debug(f'Length of {currency}_{interval} : {len(df)}')
                else:
                    logger.info(f'Init dataframe failed {currency}_{interval}')


    def update_dataframe(self):
        decay_time = 0.0
        cur_date = now(exchange=self.name, rounding_seconds=True)

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
                        logger.debug(self.data[candle].tail(3))
                        logger.debug(f'Failed to update dataframe of {candle} at {self.data[candle].index[-1]}')
                        logger.debug(f'Sleep Time : {sleep_time}')
                        self.updated_len[candle] = 0
                        self.delay_time += 0.1
                        decay_time -= 0.2
                        break

                    else:
                        df['datetime'] = [datetime.fromtimestamp(t).astimezone(self.tz) for t in df['timestamp']]
                        df.set_index(keys='datetime', inplace=True)
                        df.drop(df.index[0], inplace=True)
                        self.updated_len[candle] = update_len
                        self.data[candle].drop(self.data[candle].index[range(self.updated_len[candle])], inplace=True)
                        self.data[candle] = self.data[candle].append(df)

                        logger.debug(f'Completed updating dataframe of {candle} at {self.data[candle].index[-1]}')
                else:
                    self.updated_len[candle] = 0

            self.delay_time -= 0.2 if self.delay_time - 0.2 > 0.7 else self.delay_time
            return True

        return False


    def init_balance(self):
        self.balance = dict(
            fiat = self.init_budget
        )
        for currency in self.currencies:
            self.balance[currency] = {
                'avail': 0.0,
                'balance': 0.0
            }


    def send_orders(self):
        time_now = now(exchange=self.name)

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
        c_func='set_order'

        if isinstance(t, type(None)):
            if isinstance(o, Order):
                return self._send_order(order=o, _datetime=now(exchange=self.name))
            else:
                raise InputValueValidException(c_func=c_func, param_='o', value_=o)
        elif isinstance(t, datetime):
            if isinstance(o, Order):
                self.orders[t].append(o)
            else:
                raise InputValueValidException(c_func=c_func, param_='o', value_=o)
        else:
            raise InputValueValidException(c_func=c_func, param_='t', value_=t)


    def _send_signal(self, signal_type, trade_type, currency, price, quantity, is_safety=False, error_message=None):
        eval_balance=int(price * quantity)
        self.calc_estimated()
        profit= self.earning_rate * 100
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
        try:
            TradeApi.bot_signals(data)
        except Exception as e:
            self.exit(msg=e, stop_bot=True)


    def _update_quantity(self, update_type, order_id, currency, price, quantity, order_type, use_balance, avail, balance):
        self.balance['fiat'] += use_balance
        self.balance[currency]['avail'] += avail
        self.balance[currency]['balance'] += balance
        self._round_off_balance()

        logger.info(f'[{now(exchange=self.name)} {update_type}], order_id: {order_id}, Currency: {currency}, '
                    f'OrderType: {order_type}, Fiat: {use_balance}, Avail: {avail}, Balance: {balance}')
        logger.info(f'MY BALANCE: {self.balance}')

        if self.running_mode == 'LIVE':
            data = {
                'use_balance': use_balance,
                'exchange': self.name,
                'fiat': self.fiat,
                'currency': currency,
                'avail': avail,
                'balance': balance
            }
            try:
                TradeApi.bot_quantity(data=data)
                self._send_signal(
                    signal_type=update_type, trade_type=order_type, currency=currency, price=price, quantity=quantity
                )
            except Exception as e:
                self.exit(msg=e, stop_bot=True)
                return dict(error=e)

            return True

        else:
            return True


    def _round_off_balance(self):
        self.balance['fiat'] = round(self.balance['fiat'], self.r_off)
        for currency in self.currencies:
            self.balance[currency]['avail'] = round(self.balance[currency]['avail'], self.r_off)
            self.balance[currency]['balance'] = round(self.balance[currency]['balance'], self.r_off)

    def exit(self, msg=None, stop_bot=False):
        default_msg = ''
        msg = default_msg if msg == None else msg
        if self.running_mode == 'LIVE':
            logger.critical(msg=msg)
            TradeApi.error(error_msg=msg, stop_bot=stop_bot)
        if stop_bot:
            sys.exit()

    def set_waiting_time(self, set_time):
        self.wait_time = set_time

    def get_waiting_time(self):
        return self.wait_time

    def _send_error(self, msg, stop_bot=False):
        if self.running_mode == 'LIVE':
            TradeApi.error(error_msg=msg, stop_bot=stop_bot)

    def get_balance(self):
        return self.balance

    def get_order_list(self):
        self.update_balance()
        return self.order_list

    def get_orders(self):
        return self.orders

    def get_time(self):
        return now(exchange=self.name)

    @abstractmethod
    def update_balance(self):
        raise NotImplementedError

    @abstractmethod
    def set_cancel(self, order_id=None, qty=None):
        raise NotImplementedError

    @abstractmethod
    def calc_estimated(self):
        raise NotImplementedError


class BacktestBase(ABC):
    def __init__(self, init_budget, currency_list, interval_list, fiat=None):
        self.fiat = fiat
        self.updated_len = dict()
        self.is_update = dict()
        self.init_budget = init_budget
        self.currencies = tuple(currency_list)
        self.intervals = tuple(interval_list)

    def set_waiting_time(self, set_time):
        self.wait_time = set_time

    def get_waiting_time(self):
        return self.wait_time

    def _sned_error(self, msg, stop_bot=False):
        TradeApi.error(error_msg=msg, stop_bot=stop_bot)

    def exit(self, msg=None, stop_bot=False):
        default_msg = ''
        msg = default_msg if msg == None else msg
        logger.error(msg=msg)
        if stop_bot:
            sys.exit()

    @abstractmethod
    def init_dataframe(self):
        raise NotImplementedError

    @abstractmethod
    def update_dataframe(self):
        raise NotImplementedError

    @abstractmethod
    def init_balance(self):
        raise NotImplementedError

    @abstractmethod
    def update_balance(self):
        raise NotImplementedError

    @abstractmethod
    def set_order(self, o, t=None):
        raise NotImplementedError

    @abstractmethod
    def set_cancel(self, order_id=None, qty=None):
        raise NotImplementedError

    @abstractmethod
    def get_balance(self):
        raise NotImplementedError

    @abstractmethod
    def get_order_list(self, currency=None):
        raise NotImplementedError

    @abstractmethod
    def get_time(self):
        raise NotImplementedError

    @abstractmethod
    def calc_estimated(self):
        raise NotImplementedError
