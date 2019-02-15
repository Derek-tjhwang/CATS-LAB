# -*- coding: utf-8 -*-
"""
.. module:: momentum
   :synopsis: Momentum Indicators.

.. moduleauthor:: Dario Lopez Padial (Bukosabino)

"""
import pandas as pd
import numpy as np

from .utils import *


def rsi(close, n=14, fillna=True, is_update=False, update_number=None):
    """Relative Strength Index (RSI)

    Compares the magnitude of recent gains and losses over a specified time
    period to measure speed and change of price movements of a security. It is
    primarily used to attempt to identify overbought or oversold conditions in
    the trading of an asset.

    https://www.investopedia.com/terms/r/rsi.asp

    Args:
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.
    """
    diff = close.diff()
    which_dn = diff < 0

    up, dn = diff, diff*0
    up[which_dn], dn[which_dn] = 0, -up[which_dn]

    emaup = ema(up, n, fillna)
    emadn = ema(dn, n, fillna)

    rsi = 100 * emaup/(emaup + emadn)
    if fillna:
        rsi = rsi.replace([np.inf, -np.inf], np.nan).fillna(50)
        
    if is_update:
        return pd.Series(rsi, name='rsi').tail(update_number)
    else:
        return pd.Series(rsi, name='rsi')


def money_flow_index(high, low, close, volume, n=14, fillna=True, is_update=False, update_number=None):
    """Money Flow Index (MFI)

    Uses both price and volume to measure buying and selling pressure. It is
    positive when the typical price rises (buying pressure) and negative when
    the typical price declines (selling pressure). A ratio of positive and
    negative money flow is then plugged into an RSI formula to create an
    oscillator that moves between zero and one hundred.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:money_flow_index_mfi

    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        close(pandas.Series): dataset 'Close' column.
        volume(pandas.Series): dataset 'Volume' column.
        n(int): n period.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.

    """
    # 0 Prepare dataframe to work
    df = pd.DataFrame([high, low, close, volume]).T
    df.columns = ['High', 'Low', 'Close', 'Volume']
    df['Up_or_Down'] = 0
    df.loc[(df['Close'] > df['Close'].shift(1)), 'Up_or_Down'] = 1
    df.loc[(df['Close'] < df['Close'].shift(1)), 'Up_or_Down'] = 2

    # 1 typical price
    tp = (df['High'] + df['Low'] + df['Close']) / 3.0

    # 2 money flow
    mf = tp * df['Volume']

    # 3 positive and negative money flow with n periods
    df['1p_Positive_Money_Flow'] = 0.0
    df.loc[df['Up_or_Down'] == 1, '1p_Positive_Money_Flow'] = mf
    n_positive_mf = df['1p_Positive_Money_Flow'].rolling(n).sum()

    df['1p_Negative_Money_Flow'] = 0.0
    df.loc[df['Up_or_Down'] == 2, '1p_Negative_Money_Flow'] = mf
    n_negative_mf = df['1p_Negative_Money_Flow'].rolling(n).sum()

    # 4 money flow index
    mr = n_positive_mf / n_negative_mf
    mr = (100 - (100 / (1 + mr)))
    if fillna:
        mr = mr.replace([np.inf, -np.inf], np.nan).fillna(50)
    
    if is_update:
        return pd.Series(mr, name='mfi_'+str(n)).tail(update_number)
    else:
        return pd.Series(mr, name='mfi_'+str(n))


def tsi(close, r=25, s=13, fillna=True, is_update=False, update_number=None):
    """True strength index (TSI)

    Shows both trend direction and overbought/oversold conditions.

    https://en.wikipedia.org/wiki/True_strength_index

    Args:
        close(pandas.Series): dataset 'Close' column.
        r(int): high period.
        s(int): low period.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.
    """
    m = close - close.shift(1)
    m1 = m.ewm(r).mean().ewm(s).mean()
    m2 = abs(m).ewm(r).mean().ewm(s).mean()
    tsi = m1/m2
    tsi *= 100
    if fillna:
        tsi = tsi.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    if is_update:
        return pd.Series(tsi, name='tsi').tail(update_number)
    else:
        return pd.Series(tsi, name='tsi')


def uo(high, low, close, s=7, m=14, l=28, ws=4.0, wm=2.0, wl=1.0, fillna=True, is_update=False, update_number=None):
    """Ultimate Oscillator
    Larry Williams' (1976) signal, a momentum oscillator designed to capture momentum
    across three different timeframes.
    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:ultimate_oscillator
    BP = Close - Minimum(Low or Prior Close).
    TR = Maximum(High or Prior Close)  -  Minimum(Low or Prior Close)
    Average7 = (7-period BP Sum) / (7-period TR Sum)
    Average14 = (14-period BP Sum) / (14-period TR Sum)
    Average28 = (28-period BP Sum) / (28-period TR Sum)
    UO = 100 x [(4 x Average7)+(2 x Average14)+Average28]/(4+2+1)
    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        close(pandas.Series): dataset 'Close' column.
        s(int): short period
        m(int): medium period
        l(int): long period
        ws(float): weight of short BP average for UO
        wm(float): weight of medium BP average for UO
        wl(float): weight of long BP average for UO
        fillna(bool): if True, fill nan values with 50.
    Returns:
        pandas.Series: New feature generated.

    """
    min_l_or_pc = close.shift(1).combine(low, min)
    max_h_or_pc = close.shift(1).combine(high, max)

    bp = close - min_l_or_pc
    tr = max_h_or_pc - min_l_or_pc

    avg_s = bp.rolling(s).sum() / tr.rolling(s).sum()
    avg_m = bp.rolling(m).sum() / tr.rolling(m).sum()
    avg_l = bp.rolling(l).sum() / tr.rolling(l).sum()

    uo = 100.0 * ((ws * avg_s) + (wm * avg_m) + (wl * avg_l)) / (ws + wm + wl)
    if fillna:
        uo = uo.fillna(50)
    
    if is_update:
        return pd.Series(uo, name='uo').tail(update_number)
    else:
        return pd.Series(uo, name='uo')

def stoch_k(high, low, close, n=14, fillna=True, is_update=False, update_number=None):
    """Stochastic Oscillator
    Developed in the late 1950s by George Lane. The stochastic
    oscillator presents the location of the closing price of a
    stock in relation to the high and low range of the price
    of a stock over a period of time, typically a 14-day period.
    https://www.investopedia.com/terms/s/stochasticoscillator.asp
    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.
        fillna(bool): if True, fill nan values.
    Returns:
        pandas.Series: New feature generated.
    """
    smin = low.rolling(n).min()
    smax = high.rolling(n).max()
    stk = 100 * (close - smin) / (smax - smin)

    if fillna:
        stk = stk.replace([np.inf, -np.inf], np.nan).fillna(50)
    
    if is_update:
        return pd.Series(stk, name='stoch_k').tail(update_number)
    else:
        return pd.Series(stk, name='stoch_k')

def stoch_k_d(high, low, close, n=14, d_n=3, fillna=True, is_update=False, update_number=None):
    """Stochastic Oscillator Signal
    Shows SMA of Stochastic Oscillator. Typically a 3 day SMA.
    https://www.investopedia.com/terms/s/stochasticoscillator.asp
    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.
        d_n(int): sma period over stoch_k
        fillna(bool): if True, fill nan values.
    Returns:
        pandas.Series: New feature generated.
    """
    stk = stoch_k(high, low, close, n, fillna=fillna)
    std = stk.rolling(d_n).mean()

    if fillna:
        std = std.replace([np.inf, -np.inf], np.nan).fillna(50)
    
    if is_update:
        return pd.Series(std, name='stoch_d').tail(update_number)
    else:
        return pd.Series(std, name='stoch_d')


def wr(high, low, close, lbp=14, fillna=True, is_update=False, update_number=None):
    """Williams %R
    From: http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:williams_r
    Developed by Larry Williams, Williams %R is a momentum indicator that is the inverse of the
    Fast Stochastic Oscillator. Also referred to as %R, Williams %R reflects the level of the close
    relative to the highest high for the look-back period. In contrast, the Stochastic Oscillator
    reflects the level of the close relative to the lowest low. %R corrects for the inversion by
    multiplying the raw value by -100. As a result, the Fast Stochastic Oscillator and Williams %R
    produce the exact same lines, only the scaling is different. Williams %R oscillates from 0 to -100.

    Readings from 0 to -20 are considered overbought. Readings from -80 to -100 are considered oversold.

    Unsurprisingly, signals derived from the Stochastic Oscillator are also applicable to Williams %R.
    %R = (Highest High - Close)/(Highest High - Lowest Low) * -100

    Lowest Low = lowest low for the look-back period
    Highest High = highest high for the look-back period
    %R is multiplied by -100 correct the inversion and move the decimal.
    From: https://www.investopedia.com/terms/w/williamsr.asp
    The Williams %R oscillates from 0 to -100. When the indicator produces readings from 0 to -20, this indicates
    overbought market conditions. When readings are -80 to -100, it indicates oversold market conditions.
    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        close(pandas.Series): dataset 'Close' column.
        lbp(int): lookback period
        fillna(bool): if True, fill nan values with -50.

    Returns:
        pandas.Series: New feature generated.
    """

    hh = high.rolling(lbp).max()  # highest high over lookback period lbp
    ll = low.rolling(lbp).min()  # lowest low over lookback period lbp

    wr = -100 * (hh - close) / (hh - ll)

    if fillna:
        wr = wr.replace([np.inf, -np.inf], np.nan).fillna(-50)
    
    if is_update:
        return pd.Series(wr, name='wr').tail(update_number)
    else:
        return pd.Series(wr, name='wr')


def ao(high, low, s=5, l=34, fillna=True, is_update=False, update_number=None):
    """Awesome Oscillator
    From: https://www.tradingview.com/wiki/Awesome_Oscillator_(AO)
    The Awesome Oscillator is an indicator used to measure market momentum. AO calculates the difference of a
    34 Period and 5 Period Simple Moving Averages. The Simple Moving Averages that are used are not calculated
    using closing price but rather each bar's midpoints. AO is generally used to affirm trends or to anticipate
    possible reversals.

    From: https://www.ifcm.co.uk/ntx-indicators/awesome-oscillator
    Awesome Oscillator is a 34-period simple moving average, plotted through the central points of the bars (H+L)/2,
    and subtracted from the 5-period simple moving average, graphed across the central points of the bars (H+L)/2.
    MEDIAN PRICE = (HIGH+LOW)/2
    AO = SMA(MEDIAN PRICE, 5)-SMA(MEDIAN PRICE, 34)
    where
    SMA — Simple Moving Average.

    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        s(int): short period
        l(int): long period
        fillna(bool): if True, fill nan values with -50.

    Returns:
        pandas.Series: New feature generated.
    """

    mp = 0.5 * (high + low)
    ao = mp.rolling(s).mean() - mp.rolling(l).mean()

    if fillna:
        ao = ao.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    if is_update:
        return pd.Series(ao, name='ao').tail(update_number)
    else:
        return pd.Series(ao, name='ao')


# ======================================
# Added by COZA.

def stochastic_rsi(close, rsi_n=14, win_size=3, fillna=True, is_update=False, update_number=None):
    """Calculate stochastic RSI for given data.

    The Stochastic RSI indicator is essentially an indicator of an indicator.
    It is used in technical analysis to provide a stochastic calculation to
    the RSI indicator. This means that it is a measure of RSI relative to its
    own high/low range over a user defined period of time. The Stochastic RSI
    is an oscillator that calculates a value between 0 and 1 which is then
    plotted as a line. This indicator is primarily used for identifying overbought
    and oversold conditions.

    https://www.tradingview.com/wiki/Stochastic_RSI_(STOCH_RSI)

    Args:
        close(pandas.Series): dataset 'close' column.
        rsi_n(int):
        win_size(int):

    Returns:
        pandas.Series: stochastic RSI
    """

    so_rsi = []

    r_sr = rsi(close, n=rsi_n, fillna=fillna)

    for i, r in enumerate(r_sr):
        start = i-win_size
        start = start if start > 0 else 0
        h = r_sr[start:i+1].max()
        l = r_sr[start:i+1].min()

        val = (r-l)/(h-l+1e-14)
        so_rsi.append(val)
    
    if is_update:
        return pd.Series(so_rsi, name='SOrsi%k_' + str(win_size)).tail(update_number)
    else:
        return pd.Series(so_rsi, name='SOrsi%k_' + str(win_size))

def stochastic_rsi_k_d(close, rsi_n=14, win_size_k=3, win_size_d=3, fillna=True, is_update=False, update_number=None):
    """Calculate stochastic RSI k d for given data.

    Args:
        clsoe()
        rsi_n(int):
        win_size_k:(int):
        win_size_d(int):

    Returns:
        pandas.Series: stochastic RSI
    """

    so_rsi_k = stochastic_rsi(close,
                              rsi_n=rsi_n,
                              win_size=win_size_k, fillna=fillna)

    so_rsi_d = pd.Series(so_rsi_k.ewm(span=win_size_d,
                                      min_periods=win_size_d).mean(),
                         name='SOrsi%d_' + str(win_size_d))

    if is_update:
        return so_rsi_k.tail(update_number), so_rsi_d.tail(update_number)
    else:
        return so_rsi_k, so_rsi_d


