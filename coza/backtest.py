from coza.objects import Context, Result
from coza.api import BacktestApi
from coza.errors import InputValueValidException
from coza.utils import now
from coza.logger import logger
from datetime import datetime, timedelta
from copy import deepcopy

import pandas as pd
import sys
import os
import time


class BacktestContext(Context):
    def __init__(self, initialize, run_strategy, make_orders, user_uuid=None, model_name=None, running_mode='LOCAL',
                use_data='LIVE', data_path='data', save_result=False, return_result=True):

        if use_data.upper() not in ('LOCAL', 'LIVE'):
            raise InputValueValidException(msg='at init', use_data=use_data)
        else:
            self.use_data = use_data.upper()
        if not isinstance(data_path, str):
            raise InputValueValidException(msg='at init', data_path=data_path)
        else:
            self.data_path = data_path
        if not isinstance(save_result, bool):
            raise InputValueValidException(msg='at init', save_result=save_result)
        else:
            self.save_result = save_result
        if not isinstance(return_result, bool):
            raise InputValueValidException(msg='at init', return_result=return_result)
        else:
            self.return_result = return_result

        self.context = dict()
        self.result = dict()

        super().__init__(
            initialize=initialize, run_strategy=run_strategy, make_orders=make_orders, running_mode=running_mode)

        if self.running_mode == 'LIVE':
            try:
                if not isinstance(user_uuid, str):
                    raise InputValueValidException(msg='at init', user_uuid=user_uuid)
                else:
                    BacktestApi.initialize(user_uuid)
                if not isinstance(model_name, str):
                    raise InputValueValidException(msg='at init', model_name=model_name)
                else:
                    self.model_info = BacktestApi.get_model(model_name)
            except Exception as e:
                logger.info('Initialize failed')
                sys.exit()

        self.initialize(self)

        if use_data == 'LOCAL':
            try:
                os.listdir(data_path)
            except FileNotFoundError:
                logger.info("data path를 찾지 못 하였습니다.")
                sys.exit()


    def run(self, exchange, start_date=None, end_date=None, init_budget=10000000.0, backtest_type=None, slippage_rate=None):
        logger.debug('Start backtest')

        if backtest_type is not None:
            backtest_type = backtest_type.lower()
            if backtest_type.lower() in ('day', 'week', 'month'):
                self.backtest_type = backtest_type
                end_date = now(exchange=exchange, rounding_seconds=True) - timedelta(minutes=1)
                if backtest_type == 'day':
                    start_date = end_date - timedelta(days=1)
                elif backtest_type == 'week':
                    start_date = end_date - timedelta(days=7)
                elif backtest_type == 'month':
                    start_date = end_date - timedelta(days=30)
            else:
                raise InputValueValidException(msg='at run', backtest_type=backtest_type)
        else:
            if isinstance(start_date, (datetime, str)):
                start_date = datetime.strptime(datetime.strftime(start_date, "%Y-%m-%dT%H:%M"), "%Y-%m-%dT%H:%M")
            else:
                raise InputValueValidException(msg='at run', start_date=start_date)
            if isinstance(end_date, (datetime, str)):
                end_date = datetime.strptime(datetime.strftime(end_date, "%Y-%m-%dT%H:%M"), "%Y-%m-%dT%H:%M")
            else:
                raise InputValueValidException(msg='at run', end_date=end_date)

        if not isinstance(init_budget, (int, float)):
            raise InputValueValidException(msg='at run', init_budget=init_budget)
        if exchange in ('coinone', 'upbit'):
            self.exchange = exchange
            trade_info = self.context['trade_info'].get(exchange)
            logger.info(f'start_date : {start_date}')
            logger.info(f'end_date : {end_date}')
            logger.info(f'trade_info of exchange {exchange} : {trade_info}')

            if trade_info is not None:
                self.exchanges[exchange] = self.make_exchange(
                    exchange=exchange, start_date=start_date, end_date=end_date, init_budget=init_budget,
                    currency_list=trade_info['currency'], interval_list=trade_info['interval'],
                    fiat=trade_info['fiat'], slippage_rate=slippage_rate, use_data=self.use_data,
                    data_path=self.data_path)
                return self.backtest(self.exchanges[exchange])
            else:
                return dict(result=False, msg=f'입력한 거래소 {exchange}가 Context Trade Info에 없습니다.')
        else:
            logger.info(f'잘 못된 거래소명을 입력하셨습니다. {exchange}')
            sys.exit()


    def make_exchange(self, exchange, start_date, end_date, init_budget, currency_list, interval_list, fiat,
                      slippage_rate, use_data, data_path):
        if exchange == 'upbit':
            from coza.exchange import UpbitBacktest
            exchange = UpbitBacktest(
                start_date=start_date, end_date=end_date, init_budget=init_budget, currency_list=currency_list,
                interval_list=interval_list, fiat=fiat, slippage_rate=slippage_rate, use_data=use_data, data_path=data_path)
        elif exchange == 'coinone':
            from coza.exchange import CoinoneBacktest
            exchange = CoinoneBacktest(
                start_date=start_date, end_date=end_date, init_budget=init_budget, currency_list=currency_list,
                interval_list=interval_list, fiat=fiat, slippage_rate=slippage_rate, use_data=use_data, data_path=data_path)

        return exchange


    def backtest(self, exchange):
        logger.debug('Running Backtest...')
        created_time = now(exchange=exchange.name, rounding_seconds=True)
        base_time = time.time()
        exchange.init_dataframe()
        
        logger.debug('Running run_strategy...')
        self.run_strategy(
            self, is_update=exchange.is_update, trade_info=self.context['trade_info'],
            update_len=exchange.updated_len, data=exchange.data)
        
        exchange.init_test_dataframe()
        exchange.estimated_list.append({'date': exchange.start_date,
                                        'estimated': deepcopy(exchange.balance['fiat'])})
        
        logger.debug('Running make_orders...')
        for _datetime in pd.date_range(start=exchange.start_date, end=exchange.end_date, freq='1min'):
            is_updated = exchange.update_dataframe(_datetime)

            if is_updated:
                self.make_orders(
                    self, is_update=exchange.is_update, trade_info=self.context['trade_info'],
                    update_len=exchange.updated_len, data=exchange.data)
                exchange.update_balance(_datetime)
            else:
                continue

        estimated_dict = exchange.calc_estimated()
        exchange.max_profit = estimated_dict.get('earning_rate') if estimated_dict.get('earning_rate') > exchange.max_profit else exchange.max_profit
        exchange.max_loss = estimated_dict.get('earning_rate') if estimated_dict.get('earning_rate') < exchange.max_loss else exchange.max_loss
        exchange.estimated_list.append({'date':exchange._get_df_datetime(), 'estimated': round(estimated_dict.get('estimated'), 4)})
        elapsed_time = time.time() - base_time
        
        if self.running_mode == 'LIVE':
            if BacktestApi.user_uuid is not None:
                result_data = dict(
                    model_id=self.model_info['id'], exchange=exchange.name, created_time=created_time.strftime("%Y-%m-%d %H:%M"),
                    backtest_type=self.backtest_type, start_date=exchange.start_date.strftime("%Y-%m-%d %H:%M"),
                    end_date=exchange.end_date.strftime("%Y-%m-%d %H:%M"), init_budget=exchange.init_budget,
                    final_balance=estimated_dict.get('estimated'), total_fee=exchange.total_fee, total_slippage=exchange.total_slippage,
                    fee_rate=exchange.fee_rate, slippage_rate=exchange.slippage_rate, earning_rate=estimated_dict.get('earning_rate'),
                    max_profit=exchange.max_profit, max_loss=exchange.max_loss, estimated_list=[{'date': i['date'].strftime(
                        "%Y-%m-%d %H:%M"), 'estimated': i['estimated']} for i in exchange.estimated_list]
                )
                BacktestApi.result(result_data)
            else:
                return dict(result=False, msg='user_uuid가 입력되지 않았습니다.')
        else:
            if self.return_result:
                logger.debug(f'Backtest finished {elapsed_time}')
                self.result[exchange.name] = Result(
                    exchange=exchange.name, currencies=exchange.currencies, intervals=exchange.intervals,
                    created_time=created_time, elapsed_time=elapsed_time, start_date=exchange.start_date, end_date=exchange.end_date,
                    init_budget=exchange.init_budget, final_balance=estimated_dict.get('estimated'), estimated_list = exchange.estimated_list,
                    fiat=exchange.fiat, total_fee = exchange.total_fee, total_slippage=exchange.total_slippage,
                    fee_rate=exchange.fee_rate, slippage_rate=exchange.slippage_rate, earning_rate= estimated_dict.get('earning_rate'),
                    max_profit=exchange.max_profit, max_loss=exchange.max_loss, trade_history=exchange.trade_history,
                    data=exchange.data
                )

                del(exchange.test_df)
                del(exchange.data)

                return self.result[exchange.name]
            else:
                return dict(result=True, msg='Backtest를 완료했습니다.')


    def set_order(self, exchange, o, t=None):
        self.exchanges[exchange].set_order(o=o, t=t)

    def set_cancel(self, exchange, currency=None, order_id=None, qty=None):
        self.exchanges[exchange].send_cancel(currency=currency, order_id=order_id, qty=qty)

    def get_balance(self, exchange):
        return self.exchanges[exchange].get_balance()

    def get_order_list(self, exchange):
        return self.exchanges[exchange].get_order_list()

    def get_orders(self, exchange):
        return self.exchanges[exchange].get_orders()

    def get_time(self, exchange):
        return self.exchanges[exchange].get_time()

    def get_estimated(self, exchange):
        return self.exchanges[exchange].calc_estimated()

    def clear_balance(self, exchange):
        return self.exchanges[exchange].clear_balance()


