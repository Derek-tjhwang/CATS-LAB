from apscheduler.schedulers.blocking import  BlockingScheduler

from coza.exchange import CoinoneTrade
from coza.objects import Context
from coza.algorithms import load_functions
from coza.api import TradeApi
from coza.settings import Safety
from datetime import datetime


class BotContext(Context):

    def __init__(
            self, user_uuid = None, bot_id=None, api_key=None, secret_key=None,init_budget=None, exchange=None, initialize=None, run_strategy=None,
            make_orders=None, running_mode='LOCAL', **kwargs):
        super().__init__(
            user_uuid=user_uuid, initialize=initialize, run_strategy=run_strategy, make_orders=make_orders,
            running_mode=running_mode)
        self.running_mode = running_mode
        self.running_type = kwargs.get('running_type', 'DEV')
        self.bot_id = bot_id
        self.context = dict()
        self.exchanges = dict()
        self.running_stat = 't'

        if self.running_mode == 'LIVE':
            # user_uuid와 bot_id 입력 확인 None이면 raise Exception
            TradeApi.initialize(user_uuid=self.user_uuid, bot_id=self.bot_id)
            self.bot_info = TradeApi.bot_info()
            self._bot_code = TradeApi.bot_code()
            exchange_key = TradeApi.get_user_excAcnt(self.bot_info.get('exchange_account').get('uuid'))
            self.api_key = exchange_key.get('api_key')
            self.secret_key = exchange_key.get('secret_key')
            self.initialize, self.run_strategy, self.make_orders = load_functions(self._bot_code)
            self.initialize(self)
            self.exchange = self.bot_info.get('exchange')
            self.init_budget = self.bot_info.get('init_balance')
            self.fiat = self.bot_info.get('fiat')
            self.safety = Safety(self.bot_info.get('safety_setting'), self.bot_info.get('use_balance'))

        elif self.running_mode == 'VIRTUAL_TRADE':
            return dict(result='False', msg='아직 준비되지 않은 모드 입니다.')

        elif self.running_mode == 'LOCAL':
            self.api_key = api_key
            self.secret_key = secret_key
            self.init_budget = init_budget
            self.initialize = initialize
            self.run_strategy = run_strategy
            self.make_orders = make_orders
            self.initialize(self)
            safety_setting = self.context['trade_info'].get('safety_setting', None)

            if safety_setting is not None:
                self.safety = Safety(safety_setting, init_budget)
            self.exchange = exchange
        else:
            return None

        if self.exchange == 'coinone':
            trade_info = self.context['trade_info']['coinone']
            self.exchanges['coinone'] = CoinoneTrade(
                api_key=self.api_key, secret_key=self.secret_key, init_budget=self.init_budget,
                currency_list=trade_info.get('currency'), interval_list=trade_info.get('interval'),
                fiat=trade_info.get('fiat'), running_mode=self.running_mode)
        else:

            print("지원하지 않는 거래소 입니다.")
            return None

        self.exchanges[self.exchange].init_dataframe()
        self.run_strategy(
            self, is_update=self.exchanges[self.exchange].is_update, trade_info=self.context['trade_info'],
            update_len=self.exchanges[self.exchange].updated_len, data=self.exchanges[self.exchange].data)

        for curr_inter in self.exchanges[self.exchange].is_update.keys():
            self.exchanges[self.exchange].is_update[curr_inter] = True

    def run(self):

        sched = BlockingScheduler()
        sched.add_job(func=self._trade,
                      trigger='cron',
                      misfire_grace_time=10,
                      minute='0-59')
        sched.start()


    def _trade(self):

        exchange = self.exchange
        self.exchanges[exchange].update_balance()
        estimated = self.exchanges[exchange].calc_estimated()

        if self.running_mode == 'LIVE':
            data = dict(
                use_balance= estimated,
                profit_rate= round((estimated - self.init_budget) / self.init_budget,4) * 100,
                create_time= int(datetime.now().timestamp())
            )
            TradeApi.bot_profits(data=data)

        if hasattr(self, 'safety'):
            if self.safety.chk_safety:
                if self.safety.check(estimated):
                    self.running_stat = 'c'

        if self.running_stat == 't':
            self.exchanges[exchange].update_dataframe()
            self.run_strategy(
                self, is_update=self.exchanges[exchange].is_update, trade_info=self.context['trade_info'],
                update_len=self.exchanges[exchange].updated_len, data=self.exchanges[exchange].data)
            self.make_orders(
                self, is_update=self.exchanges[exchange].is_update, trade_info=self.context['trade_info'],
                update_len=self.exchanges[exchange].updated_len, data=self.exchanges[exchange].data)
            self.exchanges[exchange].send_orders()

        elif self.running_stat == 'c':
            self.exchanges[exchange].clear_balance()


    def set_order(self, exchange, o, t=None):
        return self.exchanges[exchange].set_order(o=o, t=t)

    def set_cancel(self, exchange, currency=None, order_id=None, qty=None):
        return self.exchanges[exchange].set_cancel(
            currency=currency, order_id=order_id, qty=qty)

    def get_balance(self, exchange):
        return self.exchanges[exchange].get_balance()

    def get_order_list(self, exchange):
        return self.exchanges[exchange].get_order_list()

    def get_orders(self, exchange):
        return self.exchanges[exchange].get_orders()

    def get_time(self, exchange):
        return self.exchanges[exchange].get_time()











