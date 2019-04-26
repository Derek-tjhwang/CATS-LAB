from abc import ABC, abstractmethod
from coza.api import TradeApi
from coza.logger import logger
from coza.errors import InputValueValidException

import sys


class Context(ABC):


    def __init__(self, initialize=None, run_strategy=None, make_orders=None, running_mode='LOCAL'):
        if running_mode.upper() not in ('LOCAL', 'LIVE'):
            raise InputValueValidException(msg='at init', running_mode=running_mode)
        else:
            self.running_mode = running_mode.upper()
        self.wait_time = dict()
        self.exchanges = dict()
        self.initialize = initialize
        self.run_strategy = run_strategy
        self.make_orders = make_orders

    def set_waiting_time(self, set_time):
        self.wait_time = set_time

    def get_waiting_time(self):
        return self.wait_time

    def _exit(self, msg=None):
        logger.info(msg=msg)
        if self.running_mode == 'LIVE':
            TradeApi.bot_stop(data=msg)
        else:
            sys.exit()

    def _stop_bot(self, msg=None):
        default_msg = 'Bot stop by Safety settings.'
        msg = default_msg if msg == None else msg
        if self.running_mode == 'LIVE':
            logger.info(msg=msg)
            TradeApi.bot_stop(data=msg)

    @abstractmethod
    def run(self):
        raise NotImplementedError

    @abstractmethod
    def set_order(self, exchange, t, o):
        raise NotImplementedError

    @abstractmethod
    def set_cancel(self, exchange, order_id=None, qty=None):
        raise NotImplementedError

    @abstractmethod
    def get_balance(self, exchange):
        raise NotImplementedError

    @abstractmethod
    def get_order_list(self, exchange, currency=None):
        raise NotImplementedError

    @abstractmethod
    def get_time(self, exchange):
        raise NotImplementedError

    @abstractmethod
    def get_estimated(self, exchange):
        raise NotImplementedError

    @abstractmethod
    def clear_balance(self, exchange):
        raise NotImplementedError


