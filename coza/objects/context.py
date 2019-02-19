from abc import ABC, abstractmethod

class Context(ABC):


    def __init__(self, user_uuid=None, initialize=None, run_strategy=None, make_orders=None, running_mode='LOCAL'):
        self.user_uuid=user_uuid
        self.running_mode = running_mode
        self.wait_time = dict()
        self.exchanges = dict()
        self.initialize = initialize
        self.run_strategy = run_strategy
        self.make_orders = make_orders

    def set_waiting_time(self, set_time):
        self.wait_time = set_time

    def get_waiting_time(self):
        return self.wait_time

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


