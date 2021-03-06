from datetime import datetime
import plotly.offline as py
import plotly.graph_objs as go
import pandas as pd
import pytz

KST = pytz.timezone('Asia/Seoul')

class Result(object):


    def __init__(self, exchange, currencies, intervals, created_time, elapsed_time, start_date, end_date, init_budget,
                 final_balance, estimated_list, fiat, total_fee, total_slippage, fee_rate, slippage_rate, earning_rate, max_profit, max_loss,
                 trade_history, data, **kwargs):
        self.test_name = kwargs.get('test_name', None)
        self.model_name = kwargs.get('model_name', None)
        self.model_id = kwargs.get('model_id', None)
        self.data = data
        self.exchange = exchange
        self.currencies = currencies
        self.intervals = intervals
        self.created_time = created_time
        self.elapsed_time = elapsed_time
        self.start_date = start_date
        self.end_date = end_date
        self.init_budget = init_budget
        self.final_balace = final_balance
        self.estimated_list = tuple(estimated_list)
        self.fiat = fiat
        self.total_fee = total_fee
        self.total_slippage = total_slippage
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate
        self.earning_rate = earning_rate
        self.max_profit = max_profit
        self.max_loss = max_loss
        self.trade_history = trade_history


    def show(self):
        pass


    def plot(self, add_marker=False, currency_list=None, main_interval=None):
        py.init_notebook_mode()
        
        if currency_list is None or type(currency_list) != list:
            currency_list = self.currencies

        if main_interval is None:
            interval = min(self.intervals)
        else:
            interval = main_interval

        a_currency = currency_list[0]
        if isinstance(self.start_date, datetime):
            start_date = self.start_date.astimezone(KST)
        elif isinstance(self.start_date, str):
            start_date = datetime.strptime(self.start_date, "%Y-%m-%dT%H:%M")

        if isinstance(self.end_date, datetime):
            end_date = self.end_date
        elif isinstance(self.end_date, str):
            end_date = datetime.strptime(self.end_date, "%Y-%m-%dT%H:%M")

        x_index = []
        for _index in list(self.data['{}_{}'.format(a_currency, interval)].index):
            if _index >= self.start_date:
                x_index.append(_index)

        df = pd.DataFrame(list(self.estimated_list))

        data = []
        data.append(go.Scatter(x=df['date'].astype('str'), y=df['estimated'], name='Change Balance', yaxis='y1'))

        for i, currency in enumerate(currency_list):
            data.append(go.Scatter(x=pd.Series(x_index).astype('str'),
                                   y=self.data['{}_{}'.format(currency, interval)]['close'][self.data['{}_{}'.format(currency, interval)]['timestamp']>=datetime.timestamp(self.start_date)],
                                   name='{} Close'.format(currency),
                                   yaxis='y{}'.format(i+2)))

        layout_list = []
        layout = go.Layout(title='Backtest Result',
                           width=1000,
                           xaxis=dict(domain=[0, 1]))

        yaxis1 = {'yaxis1': dict(title='Change Balance',
                                 titlefont=dict(color='#1f77b4'),
                                 tickfont=dict(color='#1f77b4'),
                                 anchor='x',
                                 side='left',
                                 position=0)}
        layout_list.append(yaxis1)
        for i, currency in enumerate(currency_list):
            layout_list.append({'yaxis{}'.format(i+2): dict(title='{} Close'.format(currency),
                                                            anchor='free',
                                                            overlaying='y',
                                                            side='right',
                                                            position=1-0.2*i)})

        for _layout in layout_list:
            layout.update(_layout)

        # Add markers
        if add_marker:
            BUY_list = {}
            SELL_list = {}

            for currency in currency_list:
                BUY_list['{}'.format(currency)] = []
                SELL_list['{}'.format(currency)] = []

            for order in self.trade_history:
                for _order in self.trade_history[order]['order_list']:
                    if _order.order_type == 'BUY':
                        BUY_list['{}'.format(_order.currency)].append({'date': order, 'price': _order.price})
                    else:
                        SELL_list['{}'.format(_order.currency)].append({'date': order, 'price': _order.price})

            for i, currency in enumerate(currency_list):
                if len(BUY_list['{}'.format(currency)]) != 0 and len(SELL_list['{}'.format(currency)]) !=0:
                    BUY_df = pd.DataFrame(BUY_list['{}'.format(currency)])
                    SELL_df = pd.DataFrame(SELL_list['{}'.format(currency)])

                    data.append(go.Scatter(x=BUY_df['date'].astype('str'),
                                           y=BUY_df['price'],
                                           mode='markers',
                                           name = '{} BUY-markers'.format(currency), 
                                           yaxis='y{}'.format(i+2)))
                    data.append(go.Scatter(x=SELL_df['date'].astype('str'),
                                           y=SELL_df['price'],
                                           mode='markers',
                                           name = '{} SELL-markers'.format(currency), 
                                           yaxis='y{}'.format(i+2)))
        else:
            pass            

        fig = go.Figure(data=data, layout=layout)
        py.iplot(fig)


    def plot_candle(self, currency, interval, mode='candlestick'):
        dataframe = self.data['{}_{}'.format(currency, interval)]

        x_index = []
        for _timestamp in dataframe['timestamp'].values:
            x_index.append(datetime.strftime(datetime.fromtimestamp(_timestamp), '%Y-%m-%d %H:%M:%S'))
        
        if mode == 'OHLC':
            candles = go.Ohlc(x=x_index,
                              open=dataframe['open'],
                              high=dataframe['high'],
                              low=dataframe['low'],
                              close=dataframe['close'])
        elif mode == 'candlestick':
            candles = go.Candlestick(x=x_index,
                                     open=dataframe['open'],
                                     high=dataframe['high'],
                                     low=dataframe['low'],
                                     close=dataframe['close'])
        else:
             print('지원하지 않는 모드입니다.')
        
        if mode == 'OHLC' or mode == 'candlestick':
            layout = go.Layout(title='{} {} {}min OHLC Chart'.format(self.exchange, currency, interval),
                               width=1000,
                               xaxis=dict(domain=[0, 1]))

            chart = [candles]
            
            fig = go.Figure(data=chart, layout=layout)
            py.iplot(fig)



    def _cagr_year(self, start_date=None, end_date=None):
        periods = (self.estimated_list[-1]['date'] - self.estimated_list[0]['date']).days / 365
        first = self.estimated_list[0]['estimated']
        last = self.estimated_list[-1]['estimated']

        return (last / first) ** (1 / periods) - 1


    def _cagr_month(self, start_date=None, end_date=None):
        periods = (self.estimated_list[-1]['date'] - self.estimated_list[0]['date']).days / 30
        first = self.estimated_list[0]['estimated']
        last = self.estimated_list[-1]['estimated']

        return (last / first) ** (1 / periods) - 1


    def _cagr_day(self, start_date=None, end_date=None):
        periods = (self.estimated_list[-1]['date'] - self.estimated_list[0]['date']).days
        first = self.estimated_list[0]['estimated']
        last = self.estimated_list[-1]['estimated']

        return (last / first) ** (1 / periods) - 1


    def _mdd(self):
        dd_list = []
        cur_high = None
        cur_low = None

        estimated_li = []
        for item in self.estimated_list:
            estimated_li.append(item['estimated'])

        for value in estimated_li:
            if cur_high is None:
                cur_high = value
            elif cur_low is None:
                if cur_high >= value:
                    cur_low = value
                elif cur_high < value:
                    cur_high = value
            else:
                if cur_high < value:
                    dd = (cur_high - cur_low)/cur_high * 100
                    dd_list.append(dd)
                    cur_high = value
                    cur_low = None
                elif cur_low > value:
                    cur_low = value

        if len(dd_list) == 0:
            if cur_high is not None and cur_low is not None:
                mdd = round((cur_high - cur_low)/cur_high * 100, 2)
            else:
                mdd = 0.0
        else:
            mdd = round(max(dd_list), 2)

        return mdd


    def _sharpe_ratio(self):
        # 기준 금리
        risk_free_ratio = 0.0175

        df = pd.DataFrame(self.estimated_list)
        df['return'] = round((df['estimated'] - df['estimated'].shift(1)) / df['estimated'].shift(1) * 100, 4).fillna(0)
        df['excess_return'] = df['return'] - risk_free_ratio

        if df['excess_return'].std() != 0:
            sharpe_ratio = df['excess_return'].mean() / df['excess_return'].std()
            return round(sharpe_ratio, 4)
        else:
            return 0


    def _calmar_ratio(self):
        # 기준 금리
        risk_free_ratio = 0.0175

        df = pd.DataFrame(self.estimated_list)
        df['return'] = round((df['estimated'] - df['estimated'].shift(1)) / df['estimated'].shift(1) * 100, 4).fillna(0)
        df['excess_return'] = df['return'] - risk_free_ratio

        mdd = self._mdd()

        if mdd != 0:
            calmar_ratio = df['excess_return'].mean() / mdd
            return round(calmar_ratio, 4)
        else:
            return 0

        