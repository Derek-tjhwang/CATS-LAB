from abc import ABC, abstractmethod
from collections import defaultdict


class BaseExchange(ABC):

    def __init__(self, init_budget, currency_list, interval_list, fiat=None):
        self.fiat=fiat
        self.updated_len = dict()
        self.is_update = dict()
        self.init_budget = init_budget
        self.currencies = tuple(currency_list)
        self.intervals = tuple(interval_list)

    def set_waiting_time(self, set_time):
        self.wait_time = set_time

    def get_waiting_time(self):
        return self.wait_time

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


