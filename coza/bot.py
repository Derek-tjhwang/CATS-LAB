from apscheduler.schedulers.blocking import  BlockingScheduler
from coza.algorithms import load_functions
from coza.errors import InputValueValidException
from coza.objects import Context
from coza.logger import logger
from coza.api import TradeApi
from coza.settings import Safety
from coza.utils import now


class BotContext(Context):
    def __init__(
            self, user_uuid = None, bot_id=None, api_key=None, secret_key=None,init_budget=None, exchange=None, initialize=None, run_strategy=None,
            make_orders=None, running_mode='LOCAL', running_type='SERVICE', using_api='EXCHANGE', **kwargs):
        super().__init__(
            initialize=initialize, run_strategy=run_strategy, make_orders=make_orders, running_mode=running_mode)

        if running_type.upper() not in ('DEV', 'SERVICE'):
            raise InputValueValidException(msg='at init', running_type=running_type)
        else:
            self.running_type = running_type.upper()

        self.context = dict()
        self.exchanges = dict()
        self.running_stat = 't'

        if self.running_mode == 'LIVE':
            if isinstance(user_uuid, str):
                self.user_uuid = user_uuid
            else:
                raise InputValueValidException(msg='at init', user_uuid=user_uuid)
            if isinstance(bot_id, (int, str)):
                self.bot_id = bot_id
            else:
                raise InputValueValidException(msg='at init', bot_id=bot_id)

            TradeApi.initialize(user_uuid=self.user_uuid, bot_id=self.bot_id)

            self.bot_info = TradeApi.bot_info()
            self._bot_code = TradeApi.bot_code()
            exchange_key = TradeApi.get_user_excAcnt(self.bot_info.get('exchange_account').get('uuid'))
            self.api_key = exchange_key.get('api_key')
            self.secret_key = exchange_key.get('secret_key')
            self.initialize, self.run_strategy, self.make_orders = load_functions(self._bot_code)

            if callable(self.initialize):
                self.initialize(self)
            else:
                raise InputValueValidException(msg='at init', initialize=initialize)

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
            if callable(self.initialize):
                self.initialize(self)
            else:
                raise InputValueValidException(msg='at init', initialize=initialize)
            safety_setting = self.context['trade_info'].get('safety_setting', None)

            if safety_setting is not None:
                self.safety = Safety(safety_setting, init_budget)
            self.exchange = exchange

        if not isinstance(self.api_key, str):
            raise InputValueValidException(msg='at init', api_key=api_key)
        if not isinstance(self.secret_key, str):
            raise InputValueValidException(msg='at init', secret_key=secret_key)
        if not isinstance(self.init_budget, (int, float)):
            raise InputValueValidException(msg='at init', init_budget=init_budget)
        # if not(callable(run_strategy)):
        #     raise InputValueValidException(msg='at init', run_strategy=run_strategy)
        # if not(callable(make_orders)):
        #     raise InputValueValidException(msg='at init', make_orders=make_orders)

        if self.exchange in ('coinone', 'upbit'):
            try:
                if self.exchange == 'coinone':
                    from coza.exchange import CoinoneTrade
                    trade_info = self.context['trade_info']['coinone']
                    self.exchanges['coinone'] = CoinoneTrade(
                        api_key=self.api_key, secret_key=self.secret_key, init_budget=self.init_budget,
                        currency_list=trade_info.get('currency'), interval_list=trade_info.get('interval'),
                        fiat=trade_info.get('fiat'), running_mode=self.running_mode, using_api=using_api)
                elif self.exchange == 'upbit':
                    from coza.exchange import UpbitTrade
                    trade_info = self.context['trade_info']['upbit']
                    self.exchanges['upbit'] = UpbitTrade(
                        api_key=self.api_key, secret_key=self.secret_key, init_budget=self.init_budget,
                        currency_list=trade_info.get('currency'), interval_list=trade_info.get('interval'),
                        fiat=trade_info.get('fiat'), running_mode=self.running_mode, using_api=using_api)
            except KeyError as e:
                logger.error(f'정의되지 않은 key 입니다. {e}')
                self._exit(msg=f'Exchange not define context. {e}')
            except Exception as e:
                logger.error(f'Exchange not define context. {e}')
                self._exit(msg=f'Exchange not define context. {e}')

        else:
            logger.debug(f"지원하지 않는 거래소 입니다. {self.exchange}")
            self._exit(msg=f'지원하지 않는 거래소 입니다. {self.exchange}')

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
        self.estimated = self.exchanges[exchange].calc_estimated()

        if self.running_mode == 'LIVE':
            data = dict(
                use_balance= self.estimated.get('estimated'),
                profit_rate= round((self.estimated.get('estimated') - self.init_budget) / self.init_budget,4) * 100,
                create_time= int(now(exchange=exchange, rounding_seconds=True).timestamp())
            )
            logger.info(f'Bot Profit : {data}')
            try:
                TradeApi.bot_profits(data=data)
            except Exception as e:
                logger.error(msg=e)
                TradeApi.error(error_msg='Failed send Bot profit.')

        if hasattr(self, 'safety'):
            if self.safety.chk_safety:
                logger.debug('Checking the Safety conditions...')
                if self.safety.check(self.estimated.get('estimated')):
                    logger.info('estimated : {}'.format(self.estimated.get('estimated')))
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
            if self.estimated.get('currency_ratio') < 0.01:
                self._stop_bot()
            logger.debug(f'Clear balance \n Current balance : {self.get_balance(exchange)}')
            self.exchanges[exchange].clear_balance()
            logger.info(f'Balance after clear_balance : {self.get_balance(exchange)}')

    def set_order(self, exchange, o, t=None):
        return self.exchanges[exchange].set_order(o=o, t=t)

    def set_cancel(self, exchange, currency=None, order_id=None, qty=None):
        return self.exchanges[exchange].set_cancel(currency=currency, order_id=order_id, qty=qty)

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











