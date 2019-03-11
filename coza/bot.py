from apscheduler.schedulers.blocking import  BlockingScheduler
from coza.settings import input_value_validation
from coza.algorithms import load_functions
from coza.exchange import CoinoneTrade
from coza.objects import Context
from coza.logger import logger
from coza.api import TradeApi
from coza.settings import Safety
from coza.utils import now


class BotContext(Context):
    def __init__(
            self, user_uuid = None, bot_id=None, api_key=None, secret_key=None,init_budget=None, exchange=None, initialize=None, run_strategy=None,
            make_orders=None, running_mode='LOCAL', running_type='LIVE', using_api='EXCHANGE', **kwargs):
        super().__init__(
            initialize=initialize, run_strategy=run_strategy, make_orders=make_orders, running_mode=running_mode)
        c_func='init'
        if input_value_validation(c_func=c_func, type_='C', param_='running_mode', value_=running_mode.upper()):
            self.running_mode = running_mode.upper()
        if input_value_validation(c_func=c_func, type_='C', param_='running_type', value_=running_type.upper()):
            self.running_type = running_type.upper()

        self.context = dict()
        self.exchanges = dict()
        self.running_stat = 't'

        if self.running_mode == 'LIVE':
            if input_value_validation(c_func=c_func, type_='S', param_='user_uuid', value_=user_uuid):
                self.user_uuid = user_uuid
            if input_value_validation(c_func=c_func, type_='S', param_='bot_id', value_=bot_id):
                self.bot_id = bot_id

            TradeApi.initialize(user_uuid=self.user_uuid, bot_id=self.bot_id)
            self.bot_info = TradeApi.bot_info()
            self._bot_code = TradeApi.bot_code()
            exchange_key = TradeApi.get_user_excAcnt(self.bot_info.get('exchange_account').get('uuid'))
            self.api_key = exchange_key.get('api_key')
            self.secret_key = exchange_key.get('secret_key')
            self.initialize, self.run_strategy, self.make_orders = load_functions(self._bot_code)

            input_value_validation(c_func=c_func, type_='F', param_='initialize', value_=self.initialize)
            self.initialize(self)
            self.exchange = self.bot_info.get('exchange')
            self.init_budget = self.bot_info.get('init_balance')
            self.fiat = self.bot_info.get('fiat')
            self.safety = Safety(self.bot_info.get('safety_setting'), self.bot_info.get('use_balance'))

        elif self.running_mode == 'VIRTUAL_TRADE':
            pass

        elif self.running_mode == 'LOCAL':
            self.api_key = api_key
            self.secret_key = secret_key
            self.init_budget = init_budget
            self.initialize = initialize
            self.run_strategy = run_strategy
            self.make_orders = make_orders
            input_value_validation(c_func=c_func, type_='F', param_='initialize', value_=self.initialize)
            self.initialize(self)
            safety_setting = self.context['trade_info'].get('safety_setting', None)

            if safety_setting is not None:
                self.safety = Safety(safety_setting, init_budget)
            self.exchange = exchange

        input_value_validation(c_func=c_func, type_='S', param_='api_key', value_=self.api_key)
        input_value_validation(c_func=c_func, type_='S', param_='secret_key', value_=self.secret_key)
        input_value_validation(c_func=c_func, type_='N', param_='init_budget', value_=self.init_budget)
        input_value_validation(c_func=c_func, type_='F', param_='run_strategy', value_=self.run_strategy)
        input_value_validation(c_func=c_func, type_='F', param_='make_orders', value_=self.make_orders)

        if self.exchange == 'coinone':
            try:
                trade_info = self.context['trade_info']['coinone']
                self.exchanges['coinone'] = CoinoneTrade(
                    api_key=self.api_key, secret_key=self.secret_key, init_budget=self.init_budget,
                    currency_list=trade_info.get('currency'), interval_list=trade_info.get('interval'),
                    fiat=trade_info.get('fiat'), running_mode=self.running_mode, using_api=using_api)
            except:
                logger.error('Exchange not define context.')
                quit()

        else:
            logger.debug("지원하지 않는 거래소 입니다.")
            quit()

        self.exchanges[self.exchange].init_dataframe()
        self.run_strategy(
            self, is_update=self.exchanges[self.exchange].is_update, trade_info=self.context['trade_info'],
            update_len=self.exchanges[self.exchange].updated_len, data=self.exchanges[self.exchange].data)

        for curr_inter in self.exchanges[self.exchange].is_update.keys():
            self.exchanges[self.exchange].is_update[curr_inter] = True


    def run(self):
        logger.debug('Start trade')
        
        sched = BlockingScheduler()
        sched.add_job(func=self._trade,
                      trigger='cron',
                      misfire_grace_time=10,
                      minute='0-59')
        
        sched.start()


    def _trade(self):
        logger.debug('Trading...')
        
        exchange = self.exchange
        self.exchanges[exchange].update_balance()
        estimated = self.exchanges[exchange].calc_estimated()

        if self.running_mode == 'LIVE':
            data = dict(
                use_balance= estimated.get('estimated'),
                profit_rate= round((estimated.get('estimated') - self.init_budget) / self.init_budget,4) * 100,
                create_time= int(now(exchange=exchange, rounding_seconds=True).timestamp())
            )
            logger.info(f'Bot Profit : {data}')
            TradeApi.bot_profits(data=data)

        if hasattr(self, 'safety'):
            if self.safety.chk_safety:
                logger.debug('Checking the Safety conditions...')
                if self.safety.check(estimated.get('estimated')):
                    logger.info('estimated : {}'.format(estimated.get('estimated')))
                    self.running_stat = 'c'

        if self.running_stat == 't':
            logger.debug('Updating dataframes...')
            self.exchanges[exchange].update_dataframe()
            
            logger.debug('Running run_strategy...')
            self.run_strategy(
                self, is_update=self.exchanges[exchange].is_update, trade_info=self.context['trade_info'],
                update_len=self.exchanges[exchange].updated_len, data=self.exchanges[exchange].data)
            
            logger.debug('Running make_orders...')
            self.make_orders(
                self, is_update=self.exchanges[exchange].is_update, trade_info=self.context['trade_info'],
                update_len=self.exchanges[exchange].updated_len, data=self.exchanges[exchange].data)
            
            logger.debug('Sending orders...')
            self.exchanges[exchange].send_orders()

        elif self.running_stat == 'c':
            logger.debug(f'Clear balance \n Current balance : {self.get_balance(exchange)}')
            self.exchanges[exchange].clear_balance()
            logger.info(f'Balance after clear_balance : {self.get_balance(exchange)}')

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

    def get_estimated(self, exchange):
        return self.exchanges[exchange].get_estimated()

    def clear_balance(self, exchange):
        return self.exchanges[exchange].clear_balance()

    def get_orderbook(self, exchange, currency):
        return self.exchanges[exchange].get_orderbook(currency=currency)











