# -*- coding: utf-8 -*-
"""
.. module:: trend
   :synopsis: Trend Indicators.

.. moduleauthor:: Dario Lopez Padial (Bukosabino)

"""
import pandas as pd
import numpy as np
from .utils import *


def macd(close, n_fast=12, n_slow=26, fillna=True, is_update=False, update_number=None):
    """Moving Average Convergence Divergence (MACD)

    Is a trend-following momentum indicator that shows the relationship between
    two moving averages of prices.

    https://en.wikipedia.org/wiki/MACD

    Args:
        close(pandas.Series): dataset 'Close' column.
        n_fast(int): n period short-term.
        n_slow(int): n period long-term.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.
    """
    emafast = ema(close, n_fast, fillna)
    emaslow = ema(close, n_slow, fillna)
    macd = emafast - emaslow
    if fillna:
        macd = macd.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    if is_update:
        return pd.Series(macd, name='MACD_%d_%d' % (n_fast, n_slow)).tail(update_number)
    else:
        return pd.Series(macd, name='MACD_%d_%d' % (n_fast, n_slow))


def macd_signal(close, n_fast=12, n_slow=26, n_sign=9, fillna=True, is_update=False, update_number=None):
    """Moving Average Convergence Divergence (MACD Signal)

    Shows EMA of MACD.

    https://en.wikipedia.org/wiki/MACD

    Args:
        close(pandas.Series): dataset 'Close' column.
        n_fast(int): n period short-term.
        n_slow(int): n period long-term.
        n_sign(int): n period to signal.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.
    """
    emafast = ema(close, n_fast, fillna)
    emaslow = ema(close, n_slow, fillna)
    macd = emafast - emaslow
    macd_signal = ema(macd, n_sign, fillna)
    if fillna:
        macd_signal = macd_signal.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    if is_update:
        return pd.Series(macd_signal, name='MACD_sign').tail(update_number)
    else:
        return pd.Series(macd_signal, name='MACD_sign')


def macd_diff(close, n_fast=12, n_slow=26, n_sign=9, fillna=True, is_update=False, update_number=None):
    """Moving Average Convergence Divergence (MACD Diff)

    Shows the relationship between MACD and MACD Signal.

    https://en.wikipedia.org/wiki/MACD

    Args:
        close(pandas.Series): dataset 'Close' column.
        n_fast(int): n period short-term.
        n_slow(int): n period long-term.
        n_sign(int): n period to signal.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.
    """
    emafast = ema(close, n_fast, fillna)
    emaslow = ema(close, n_slow, fillna)
    macd = emafast - emaslow
    macdsign = ema(macd, n_sign, fillna)
    macd_diff = macd - macdsign
    if fillna:
        macd_diff = macd_diff.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    if is_update:
        return pd.Series(macd_diff, name='MACD_diff').tail(update_number)
    else:
        return pd.Series(macd_diff, name='MACD_diff')


def ema_indicator(close, n=12, fillna=False, is_update=False, update_number=None):
    """EMA
    Exponential Moving Average via Pandas
    Args:
        close(pandas.Series): dataset 'Close' column.
        n_fast(int): n period short-term.
        fillna(bool): if True, fill nan values.
    Returns:
        pandas.Series: New feature generated.
    """
    ema_ = ema(close, n, fillna)
    
    if is_update:
        return pd.Series(ema_, name='ema').tail(update_number)
    else:
        return pd.Series(ema_, name='ema')


def adx(high, low, close, n=14, fillna=True, is_update=False, update_number=None):
    """Average Directional Movement Index (ADX)

    The Plus Directional Indicator (+DI) and Minus Directional Indicator (-DI)
    are derived from smoothed averages of these differences, and measure trend
    direction over time. These two indicators are often referred to collectively
    as the Directional Movement Indicator (DMI).

    The Average Directional Index (ADX) is in turn derived from the smoothed
    averages of the difference between +DI and -DI, and measures the strength
    of the trend (regardless of direction) over time.

    Using these three indicators together, chartists can determine both the
    direction and strength of the trend.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:average_directional_index_adx

    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.
    """
    cs = close.shift(1)

    tr = high.combine(cs, max) - low.combine(cs, min)
    trs = tr.rolling(n).sum()

    up = high - high.shift(1)
    dn = low.shift(1) - low

    pos = ((up > dn) & (up > 0)) * up
    neg = ((dn > up) & (dn > 0)) * dn

    dip = 100 * pos.rolling(n).sum() / trs
    din = 100 * neg.rolling(n).sum() / trs

    dx = 100 * np.abs((dip - din)/(dip + din))
    adx = ema(dx, n)

    if fillna:
        adx = adx.replace([np.inf, -np.inf], np.nan).fillna(40)

    if is_update:
        return pd.Series(adx, name='adx').tail(update_number)
    else:
        return pd.Series(adx, name='adx')


def adx_pos(high, low, close, n=14, fillna=True, is_update=False, update_number=None):
    """Average Directional Movement Index Positive (ADX)

    The Plus Directional Indicator (+DI) and Minus Directional Indicator (-DI)
    are derived from smoothed averages of these differences, and measure trend
    direction over time. These two indicators are often referred to collectively
    as the Directional Movement Indicator (DMI).

    The Average Directional Index (ADX) is in turn derived from the smoothed
    averages of the difference between +DI and -DI, and measures the strength
    of the trend (regardless of direction) over time.

    Using these three indicators together, chartists can determine both the
    direction and strength of the trend.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:average_directional_index_adx

    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.
    """
    cs = close.shift(1)

    tr = high.combine(cs, max) - low.combine(cs, min)
    trs = tr.rolling(n).sum()

    up = high - high.shift(1)
    dn = low.shift(1) - low

    pos = ((up > dn) & (up > 0)) * up
    neg = ((dn > up) & (dn > 0)) * dn

    dip = 100 * pos.rolling(n).sum() / trs

    if fillna:
        dip = dip.replace([np.inf, -np.inf], np.nan).fillna(20)
    
    if is_update:
        return pd.Series(dip, name='adx_pos').tail(update_number)
    else:
        return pd.Series(dip, name='adx_pos')


def adx_neg(high, low, close, n=14, fillna=True, is_update=False, update_number=None):
    """Average Directional Movement Index Negative (ADX)

    The Plus Directional Indicator (+DI) and Minus Directional Indicator (-DI)
    are derived from smoothed averages of these differences, and measure trend
    direction over time. These two indicators are often referred to collectively
    as the Directional Movement Indicator (DMI).

    The Average Directional Index (ADX) is in turn derived from the smoothed
    averages of the difference between +DI and -DI, and measures the strength
    of the trend (regardless of direction) over time.

    Using these three indicators together, chartists can determine both the
    direction and strength of the trend.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:average_directional_index_adx

    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.
    """
    cs = close.shift(1)

    tr = high.combine(cs, max) - low.combine(cs, min)
    trs = tr.rolling(n).sum()

    up = high - high.shift(1)
    dn = low.shift(1) - low

    pos = ((up > dn) & (up > 0)) * up
    neg = ((dn > up) & (dn > 0)) * dn

    din = 100 * neg.rolling(n).sum() / trs

    if fillna:
        din = din.replace([np.inf, -np.inf], np.nan).fillna(20)
    
    if is_update:
        return pd.Series(din, name='adx_neg').tail(update_number)
    else:
        return pd.Series(din, name='adx_neg')


def adx_indicator(high, low, close, n=14, fillna=True, is_update=False, update_number=None):
    """Average Directional Movement Index Indicator (ADX)

    Returns 1, if Plus Directional Indicator (+DI) is higher than Minus
    Directional Indicator (-DI). Else, return 0.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:average_directional_index_adx

    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.
    """
    cs = close.shift(1)

    tr = high.combine(cs, max) - low.combine(cs, min)
    trs = tr.rolling(n).sum()

    up = high - high.shift(1)
    dn = low.shift(1) - low

    pos = ((up > dn) & (up > 0)) * up
    neg = ((dn > up) & (dn > 0)) * dn

    dip = 100 * pos.rolling(n).sum() / trs
    din = 100 * neg.rolling(n).sum() / trs

    adx_diff = dip - din

    # prepare indicator
    df = pd.DataFrame([adx_diff]).T
    df.columns = ['adx_diff']
    df['adx_ind'] = 0
    df.loc[df['adx_diff'] > 0, 'adx_ind'] = 1
    adx_ind = df['adx_ind']

    if fillna:
        adx_ind = adx_ind.fillna(0)
    
    if is_update:
        return pd.Series(adx_ind, name='adx_ind').tail(update_number)
    else:
        return pd.Series(adx_ind, name='adx_ind')


def vortex_indicator_pos(high, low, close, n=14, fillna=True, is_update=False, update_number=None):
    """Vortex Indicator (VI)

    It consists of two oscillators that capture positive and negative trend
    movement. A bullish signal triggers when the positive trend indicator
    crosses above the negative trend indicator or a key level.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:vortex_indicator

    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.
    """
    tr = high.combine(close.shift(1), max) - low.combine(close.shift(1), min)
    trn = tr.rolling(n).sum()

    vmp = np.abs(high - low.shift(1))
    vmm = np.abs(low - high.shift(1))

    vip = vmp.rolling(n).sum() / trn
    if fillna:
        vip = vip.replace([np.inf, -np.inf], np.nan).fillna(1)
    
    if is_update:
        return pd.Series(vip, name='vip').tail(update_number)
    else:
        return pd.Series(vip, name='vip')


def vortex_indicator_neg(high, low, close, n=14, fillna=True, is_update=False, update_number=None):
    """Vortex Indicator (VI)

    It consists of two oscillators that capture positive and negative trend
    movement. A bearish signal triggers when the negative trend indicator
    crosses above the positive trend indicator or a key level.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:vortex_indicator

    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.
    """
    tr = high.combine(close.shift(1), max) - low.combine(close.shift(1), min)
    trn = tr.rolling(n).sum()

    vmp = np.abs(high - low.shift(1))
    vmm = np.abs(low - high.shift(1))

    vin = vmm.rolling(n).sum() / trn
    if fillna:
        vin = vin.replace([np.inf, -np.inf], np.nan).fillna(1)
    
    if is_update:
        return pd.Series(vin, name='vin').tail(update_number) 
    else:
        return pd.Series(vin, name='vin')


def trix(close, n=15, fillna=True, is_update=False, update_number=None):
    """Trix (TRIX)

    Shows the percent rate of change of a triple exponentially smoothed moving
    average.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:trix

    Args:
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.
    """
    ema1 = ema(close, n, fillna)
    ema2 = ema(ema1, n, fillna)
    ema3 = ema(ema2, n, fillna)
    trix = (ema3 - ema3.shift(1)) / ema3.shift(1)
    trix *= 100
    if fillna:
        trix = trix.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    if is_update:
        return pd.Series(trix, name='trix_' + str(n)).tail(update_number)
    else:
        return pd.Series(trix, name='trix_' + str(n))


def mass_index(high, low, n=9, n2=25, fillna=True, is_update=False, update_number=None):
    """Mass Index (MI)

    It uses the high-low range to identify trend reversals based on range
    expansions. It identifies range bulges that can foreshadow a reversal of the
    current trend.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:mass_index

    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        n(int): n low period.
        n2(int): n high period.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.

    """
    amplitude = high - low
    ema1 = ema(amplitude, n, fillna)
    ema2 = ema(ema1, n, fillna)
    mass = ema1 / ema2
    mass = mass.rolling(n2).sum()
    if fillna:
        mass = mass.replace([np.inf, -np.inf], np.nan).fillna(n2)
    
    if is_update:
        return pd.Series(mass, name='mass_index_' + str(n)).tail(update_number)
    else:
        return pd.Series(mass, name='mass_index_' + str(n))


def cci(high, low, close, n=20, c=0.015, fillna=True, is_update=False, update_number=None):
    """Commodity Channel Index (CCI)

    CCI measures the difference between a security's price change and its
    average price change. High positive readings indicate that prices are well
    above their average, which is a show of strength. Low negative readings
    indicate that prices are well below their average, which is a show of
    weakness.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:commodity_channel_index_cci

    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.
        c(int): constant.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.

    """
    pp = (high+low+close)/3
    cci = (pp-pp.rolling(n).mean())/pp.rolling(n).std()
    cci = 1/c * cci
    if fillna:
        cci = cci.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    if is_update:
        return pd.Series(cci, name='cci').tail(update_number)
    else:
        return pd.Series(cci, name='cci')


def dpo(close, n=20, fillna=True, is_update=False, update_number=None):
    """Detrended Price Oscillator (DPO)

    Is an indicator designed to remove trend from price and make it easier to
    identify cycles.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:detrended_price_osci

    Args:
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.
    """
    dpo = close.shift(int((0.5 * n) + 1)) - close.rolling(n).mean()
    if fillna:
        dpo = dpo.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    if is_update:
        return pd.Series(dpo, name='dpo_'+str(n)).tail(update_number)
    else:
        return pd.Series(dpo, name='dpo_'+str(n))


def kst(close, r1=10, r2=15, r3=20, r4=30, n1=10, n2=10, n3=10, n4=15, fillna=True, is_update=False, update_number=None):
    """KST Oscillator (KST)

    It is useful to identify major stock market cycle junctures because its
    formula is weighed to be more greatly influenced by the longer and more
    dominant time spans, in order to better reflect the primary swings of stock
    market cycle.

    https://en.wikipedia.org/wiki/KST_oscillator

    Args:
        close(pandas.Series): dataset 'Close' column.
        r1(int): r1 period.
        r2(int): r2 period.
        r3(int): r3 period.
        r4(int): r4 period.
        n1(int): n1 smoothed period.
        n2(int): n2 smoothed period.
        n3(int): n3 smoothed period.
        n4(int): n4 smoothed period.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.
    """
    rocma1 = ((close - close.shift(r1)) / close.shift(r1)).rolling(n1).mean()
    rocma2 = ((close - close.shift(r2)) / close.shift(r2)).rolling(n2).mean()
    rocma3 = ((close - close.shift(r3)) / close.shift(r3)).rolling(n3).mean()
    rocma4 = ((close - close.shift(r4)) / close.shift(r4)).rolling(n4).mean()
    kst = 100*(rocma1 + 2*rocma2 + 3*rocma3 + 4*rocma4)
    if fillna:
        kst = kst.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    if is_update:
        return pd.Series(kst, name='kst').tail(update_number)
    else:
        return pd.Series(kst, name='kst')


def kst_sig(close, r1=10, r2=15, r3=20, r4=30, n1=10, n2=10, n3=10, n4=15, nsig=9, fillna=True, is_update=False, update_number=None):
    """KST Oscillator (KST Signal)

    It is useful to identify major stock market cycle junctures because its
    formula is weighed to be more greatly influenced by the longer and more
    dominant time spans, in order to better reflect the primary swings of stock
    market cycle.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:know_sure_thing_kst

    Args:
        close(pandas.Series): dataset 'Close' column.
        r1(int): r1 period.
        r2(int): r2 period.
        r3(int): r3 period.
        r4(int): r4 period.
        n1(int): n1 smoothed period.
        n2(int): n2 smoothed period.
        n3(int): n3 smoothed period.
        n4(int): n4 smoothed period.
        nsig(int): n period to signal.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.
    """
    rocma1 = ((close - close.shift(r1)) / close.shift(r1)).rolling(n1).mean()
    rocma2 = ((close - close.shift(r2)) / close.shift(r2)).rolling(n2).mean()
    rocma3 = ((close - close.shift(r3)) / close.shift(r3)).rolling(n3).mean()
    rocma4 = ((close - close.shift(r4)) / close.shift(r4)).rolling(n4).mean()
    kst = 100*(rocma1 + 2*rocma2 + 3*rocma3 + 4*rocma4)
    kst_sig = kst.rolling(nsig).mean()
    if fillna:
        kst_sig = kst_sig.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    if is_update:
        return pd.Series(kst_sig, name='kst_sig').tail(update_number)
    else:
        return pd.Series(kst_sig, name='kst_sig')


def ichimoku_a(high, low, n1=9, n2=26, visual=False, fillna=True, is_update=False, update_number=None):
    """Ichimoku Kinkō Hyō (Ichimoku)

    It identifies the trend and look for potential signals within that trend.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:ichimoku_cloud

    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        n1(int): n1 low period.
        n2(int): n2 medium period.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.
    """
    conv = 0.5 * (high.rolling(n1).max() + low.rolling(n1).min())
    base = 0.5 * (high.rolling(n2).max() + low.rolling(n2).min())

    spana = 0.5 * (conv + base)

    if visual:
        spana = spana.shift(n2)

    if fillna:
        spana = spana.replace([np.inf, -np.inf], np.nan).fillna(method='backfill')

    if is_update:
        return pd.Series(spana, name='ichimoku_a_' + str(n2)).tail(update_number)
    else:
        return pd.Series(spana, name='ichimoku_a_' + str(n2))


def ichimoku_b(high, low, n2=26, n3=52, visual=False, fillna=True, is_update=False, update_number=None):
    """Ichimoku Kinkō Hyō (Ichimoku)

    It identifies the trend and look for potential signals within that trend.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:ichimoku_cloud

    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        n2(int): n2 medium period.
        n3(int): n3 high period.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.
    """
    spanb = 0.5 * (high.rolling(n3).max() + low.rolling(n3).min())

    if visual:
        spanb = spanb.shift(n2)

    if fillna:
        spanb = spanb.replace([np.inf, -np.inf], np.nan).fillna(method='backfill')

    if is_update:
        return pd.Series(spanb, name='ichimoku_b_' + str(n2)).tail(update_number)
    else:
        return pd.Series(spanb, name='ichimoku_b_' + str(n2))


def aroon_up(close, n=25, fillna=False, is_update=False, update_number=None):
    """Aroon Indicator (AI)
    Identify when trends are likely to change direction (uptrend).
    Aroon Up - ((N - Days Since N-day High) / N) x 100
    https://www.investopedia.com/terms/a/aroon.asp
    Args:
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.
        fillna(bool): if True, fill nan values.
    Returns:
        pandas.Series: New feature generated.
    """
    aroon_up = close.rolling(n).apply(lambda x: float(np.argmax(x) + 1) / n * 100)
    if fillna:
        aroon_up = aroon_up.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    if is_update:
        return pd.Series(aroon_up, name='aroon_up'+str(n)).tail(update_number)
    else:
        return pd.Series(aroon_up, name='aroon_up'+str(n))


def aroon_down(close, n=25, fillna=False, is_update=False, update_number=None):
    """Aroon Indicator (AI)
    Identify when trends are likely to change direction (downtrend).
    Aroon Down - ((N - Days Since N-day Low) / N) x 100
    https://www.investopedia.com/terms/a/aroon.asp
    Args:
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.
        fillna(bool): if True, fill nan values.
    Returns:
        pandas.Series: New feature generated.
    """
    aroon_down = close.rolling(n).apply(lambda x: float(np.argmin(x) + 1) / n * 100)
    if fillna:
        aroon_down = aroon_down.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    if is_update:
        return pd.Series(aroon_down, name='aroon_down'+str(n)).tail(update_number)
    else:
        return pd.Series(aroon_down, name='aroon_down'+str(n))
