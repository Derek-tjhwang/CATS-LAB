from beautifultable import BeautifulTable
from coza.utils import truncate


class OrderQuantity(object):
    order_types = ['ALLIN', 'PRICE', 'QUANTITY']

    def __init__(self, buy_type='ALLIN', buy_amount=0, sell_type='ALLIN', sell_amount=0):
        assert isinstance(buy_type, str) and buy_type in self.order_types, \
            f'buy_type은 {", ".join(self.order_types)} 만 가능합니다.'
        assert isinstance(buy_amount, float) or isinstance(buy_amount, int), \
            'buy_amount는 float 또는 int만 가능합니다.'
        assert isinstance(sell_type, str) and sell_type in self.order_types, \
            f'sell_type은 {", ".join(self.order_types)} 만 가능합니다.'
        assert isinstance(sell_amount, float) or isinstance(sell_amount, int), \
            'sell_amount는 float 또는 int만 가능합니다.'

        self.buy_type = buy_type
        self.buy_amount = buy_amount
        self.sell_type = sell_type
        self.sell_amount = sell_amount

    def __str__(self):
        table = BeautifulTable()
        table.column_headers = ['key', 'value']
        table.append_row(['buy_type', self.buy_type])
        table.append_row(['buy_amount', self.buy_amount])
        table.append_row(['sell_type', self.sell_type])
        table.append_row(['sell_amount', self.sell_amount])

        return table.get_string()


    def get_buy_quantity(self, budget, price):
        max_orderable_quantity = float(budget) / price
        if self.buy_type == 'ALLIN':
            quantity = max_orderable_quantity
        elif self.buy_type == 'PRICE':
            quantity = min(float(self.buy_amount) / price, max_orderable_quantity)
        else:
            quantity = min(self.buy_amount, max_orderable_quantity)
        quantity = truncate(quantity, 4)

        return quantity


    def get_sell_quantity(self, coins, price):
        max_orderable_quantity = coins
        if self.sell_type == 'ALLIN':
            quantity = max_orderable_quantity
        elif self.sell_type == 'PRICE':
            quantity = min(float(self.sell_amount) / price, max_orderable_quantity)
        else:
            quantity = min(self.sell_amount, max_orderable_quantity)
        quantity = truncate(quantity, 4)

        return quantity


class Safety(object):

    def __init__(self, safety_setting, init_budget):
        self.init_budget = init_budget
        self.high_price = 0
        self.pt_checked = safety_setting.get('profit_target').get('checked')
        self.pt_ratio = safety_setting.get('profit_target').get('ratio')
        self.sl_checked = safety_setting.get('stop_loss').get('checked')
        self.sl_ratio = safety_setting.get('stop_loss').get('ratio')
        self.ts_checked = safety_setting.get('trailing_stop').get('checked')
        self.ts_inc_ratio = safety_setting.get('trailing_stop').get('inc_ratio')
        self.ts_dec_ratio = safety_setting.get('trailing_stop').get('dec_ratio')
        self.ts_touch_inc = False
        self.chk_safety = self.pt_checked or self.sl_checked or self.ts_checked


    def _profit_target(self, estimated):
        if estimated > self.init_budget * (1 + self.pt_ratio):
            return True
        else:
            return False


    def _stop_loss(self, estimated):
        if estimated < self.init_budget * (1 - self.sl_ratio):
            return True
        else:
            return False


    def _trailling_stop(self, estimated):
        if self.ts_touch_inc:
            if estimated > self.high_price:
                self.high_price = estimated
            elif estimated < self.high_price * (1 - self.ts_dec_ratio):
                return True
            return False

        else:
            if estimated > self.init_budget * (1 + self.ts_inc_ratio):
                self.high_price = estimated
                self.ts_touch_inc = True
                return False


    def check(self, estimted):
        if self.pt_checked and self._profit_target(estimted):
            return True
        if self.sl_checked and self._stop_loss(estimted):
            return True
        if self.ts_checked and self._trailling_stop(estimted):
            return True

