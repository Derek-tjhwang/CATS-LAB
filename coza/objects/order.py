import math

class Order(object):
    def __init__(self, currency, order_type, quantity, price, fiat, is_safety=False):
        self.order_type = str(order_type).upper()
        self.currency = str(currency).lower()
        self.fiat = str(fiat).lower()
        self.price = float(price)
        self.quantity = math.floor(quantity * 10**4) / (10**4)
        self.is_safety = bool(is_safety)

    def __repr__(self):
        return f'[{self.order_type}] {self.currency}_{self.fiat} {self.price} x {self.quantity}'

    def __str__(self):
        return self.__repr__()
