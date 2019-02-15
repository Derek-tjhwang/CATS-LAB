# -*- coding: utf-8 -*-
"""
.. module:: volatility
   :synopsis: Volatility Indicators.

.. moduleauthor:: Dario Lopez Padial (Bukosabino)

"""

import numpy as np

from .utils import *


def average_true_range(high, low, close, n=14, fillna=True, is_update=False, update_number=None):
    """Average True Range (ATR)

    The indicator provide an indication of the degree of price volatility.
    Strong moves, in either direction, are often accompanied by large ranges,
    or large True Ranges.

    http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:average_true_range_atr

    Args:

        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.

    Returns:
        pandas.Series: New feature generated.
    """
    cs = close.shift(1)
    tr = high.combine(cs, max) - low.combine(cs, min)

    atr = np.zeros(len(close))
    atr[0] = tr[1::].mean()
    for i in range(1, len(atr)):
        atr[i] = (atr[i - 1] * (n - 1) + tr.iloc[i]) / float(n)

    atr = pd.Series(data=atr, index=tr.index)

    if fillna:
        atr = atr.replace([np.inf, -np.inf], np.nan).fillna(0)

    if is_update:
        return pd.Series(atr, name='atr').tail(update_number)
    else:
        return pd.Series(atr, name='atr')


def bollinger_mavg(close, n=20, fillna=True, is_update=False, update_number=None):
    """Bollinger Bands (BB)

    N-period simple moving average (MA).

    https://en.wikipedia.org/wiki/Bollinger_Bands

    Args:
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.

    Returns:
        pandas.Series: New feature generated.
    """
    mavg = close.rolling(n).mean()
    if fillna:
        mavg = mavg.replace([np.inf, -np.inf], np.nan).fillna(method='backfill')
    
    if is_update:
        return pd.Series(mavg, name='mavg').tail(update_number)
    else:
        return pd.Series(mavg, name='mavg')


def bollinger_hband(close, n=20, ndev=2, fillna=True, is_update=False, update_number=None):
    """Bollinger Bands (BB)

    Upper band at K times an N-period standard deviation above the moving
    average (MA + Kdeviation).

    https://en.wikipedia.org/wiki/Bollinger_Bands

    Args:
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.
        ndev(int): n factor standard deviation

    Returns:
        pandas.Series: New feature generated.
    """
    mavg = close.rolling(n).mean()
    mstd = close.rolling(n).std()
    hband = mavg + ndev*mstd
    if fillna:
        hband = hband.replace([np.inf, -np.inf], np.nan).fillna(method='backfill')
        
    if is_update:
        return pd.Series(hband, name='hband').tail(update_number)
    else:
        return pd.Series(hband, name='hband')


def bollinger_lband(close, n=20, ndev=2, fillna=True, is_update=False, update_number=None):
    """Bollinger Bands (BB)

    Lower band at K times an N-period standard deviation below the moving
    average (MA − Kdeviation).

    https://en.wikipedia.org/wiki/Bollinger_Bands

    Args:
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.
        ndev(int): n factor standard deviation

    Returns:
        pandas.Series: New feature generated.
    """
    mavg = close.rolling(n).mean()
    mstd = close.rolling(n).std()
    lband = mavg - ndev*mstd
    if fillna:
        lband = lband.replace([np.inf, -np.inf], np.nan).fillna(method='backfill')
    
    if is_update:
        return pd.Series(lband, name='lband').tail(update_number)
    else:
        return pd.Series(lband, name='lband')


def bollinger_hband_indicator(close, n=20, ndev=2, fillna=True, is_update=False, update_number=None):
    """Bollinger High Band Indicator

    Returns 1, if close is higher than bollinger high band. Else, return 0.

    https://en.wikipedia.org/wiki/Bollinger_Bands

    Args:
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.
        ndev(int): n factor standard deviation

    Returns:
        pandas.Series: New feature generated.
    """
    df = pd.DataFrame([close]).transpose()
    mavg = close.rolling(n).mean()
    mstd = close.rolling(n).std()
    hband = mavg + ndev*mstd
    df['hband'] = 0.0
    df.loc[close > hband, 'hband'] = 1.0
    hband = df['hband']
    if fillna:
        hband = hband.replace([np.inf, -np.inf], np.nan).fillna(0)
        
    if is_update:
        return pd.Series(hband, name='bbihband').tail(update_number)
    else:
        return pd.Series(hband, name='bbihband')


def bollinger_lband_indicator(close, n=20, ndev=2, fillna=True, is_update=False, update_number=None):
    """Bollinger Low Band Indicator

    Returns 1, if close is lower than bollinger low band. Else, return 0.

    https://en.wikipedia.org/wiki/Bollinger_Bands

    Args:
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.
        ndev(int): n factor standard deviation

    Returns:
        pandas.Series: New feature generated.
    """
    df = pd.DataFrame([close]).transpose()
    mavg = close.rolling(n).mean()
    mstd = close.rolling(n).std()
    lband = mavg - ndev*mstd
    df['lband'] = 0.0
    df.loc[close < lband, 'lband'] = 1.0
    lband = df['lband']
    if fillna:
        lband = lband.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    if is_update:
        return pd.Series(lband, name='bbilband').tail(update_number)
    else:
        return pd.Series(lband, name='bbilband')


def keltner_channel_central(high, low, close, n=10, fillna=True, is_update=False, update_number=None):
    """Keltner channel (KC)

    Showing a simple moving average line (central) of typical price.

    https://en.wikipedia.org/wiki/Keltner_channel

    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.

    Returns:
        pandas.Series: New feature generated.
    """
    tp = (high + low + close) / 3.0
    tp = tp.rolling(n).mean()
    if fillna:
        tp = tp.replace([np.inf, -np.inf], np.nan).fillna(method='backfill')
        
    if is_update:
        return pd.Series(tp, name='kc_central').tail(update_number)
    else:
        return pd.Series(tp, name='kc_central')


def keltner_channel_hband(high, low, close, n=10, fillna=True, is_update=False, update_number=None):
    """Keltner channel (KC)

    Showing a simple moving average line (high) of typical price.

    https://en.wikipedia.org/wiki/Keltner_channel

    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.

    Returns:
        pandas.Series: New feature generated.
    """
    tp = ((4*high) - (2*low) + close) / 3.0
    tp = tp.rolling(n).mean()
    if fillna:
        tp = tp.replace([np.inf, -np.inf], np.nan).fillna(method='backfill')
    
    if is_update:
        return pd.Series(tp, name='kc_hband').tail(update_number)
    else:
        return pd.Series(tp, name='kc_hband')


def keltner_channel_lband(high, low, close, n=10, fillna=True, is_update=False, update_number=None):
    """Keltner channel (KC)

    Showing a simple moving average line (low) of typical price.

    https://en.wikipedia.org/wiki/Keltner_channel

    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.

    Returns:
        pandas.Series: New feature generated.
    """
    tp = ((-2*high) + (4*low) + close) / 3.0
    tp = tp.rolling(n).mean()
    if fillna:
        tp = tp.replace([np.inf, -np.inf], np.nan).fillna(method='backfill')
    
    if is_update:
        return pd.Series(tp, name='kc_lband').tail(update_number)
    else:
        return pd.Series(tp, name='kc_lband')


def keltner_channel_hband_indicator(high, low, close, n=10, fillna=True, is_update=False, update_number=None):
    """Keltner Channel High Band Indicator (KC)

    Returns 1, if close is higher than keltner high band channel. Else,
    return 0.

    https://en.wikipedia.org/wiki/Keltner_channel

    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.

    Returns:
        pandas.Series: New feature generated.
    """
    df = pd.DataFrame([close]).transpose()
    df['hband'] = 0.0
    hband = ((4*high) - (2*low) + close) / 3.0
    df.loc[close > hband, 'hband'] = 1.0
    hband = df['hband']
    if fillna:
        hband = hband.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    if is_update:
        return pd.Series(hband, name='kci_hband').tail(update_number)
    else:
        return pd.Series(hband, name='kci_hband')


def keltner_channel_lband_indicator(high, low, close, n=10, fillna=True, is_update=False, update_number=None):
    """Keltner Channel Low Band Indicator (KC)

    Returns 1, if close is lower than keltner low band channel. Else, return 0.

    https://en.wikipedia.org/wiki/Keltner_channel

    Args:
        high(pandas.Series): dataset 'High' column.
        low(pandas.Series): dataset 'Low' column.
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.

    Returns:
        pandas.Series: New feature generated.
    """
    df = pd.DataFrame([close]).transpose()
    df['lband'] = 0.0
    lband = ((-2*high) + (4*low) + close) / 3.0
    df.loc[close < lband, 'lband'] = 1.0
    lband = df['lband']
    if fillna:
        lband = lband.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    if is_update:
        return pd.Series(lband, name='kci_lband').tail(update_number)
    else:
        return pd.Series(lband, name='kci_lband')


def donchian_channel_hband(close, n=20, fillna=True, is_update=False, update_number=None):
    """Donchian channel (DC)

    The upper band marks the highest price of an issue for n periods.

    https://www.investopedia.com/terms/d/donchianchannels.asp

    Args:
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.

    Returns:
        pandas.Series: New feature generated.
    """
    hband = close.rolling(n).max()
    if fillna:
        hband = hband.replace([np.inf, -np.inf], np.nan).fillna(method='backfill')
    
    if is_update:
        return pd.Series(hband, name='dchband').tail(update_number)
    else:
        return pd.Series(hband, name='dchband')


def donchian_channel_lband(close, n=20, fillna=True, is_update=False, update_number=None):
    """Donchian channel (DC)

    The lower band marks the lowest price for n periods.

    https://www.investopedia.com/terms/d/donchianchannels.asp

    Args:
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.

    Returns:
        pandas.Series: New feature generated.
    """
    lband = close.rolling(n).min()
    if fillna:
        lband = lband.replace([np.inf, -np.inf], np.nan).fillna(method='backfill')
    
    if is_update:
        return pd.Series(lband, name='dclband').tail(update_number)
    else:
        return pd.Series(lband, name='dclband')


def donchian_channel_hband_indicator(close, n=20, fillna=True, is_update=False, update_number=None):
    """Donchian High Band Indicator

    Returns 1, if close is higher than donchian high band channel. Else,
    return 0.

    https://www.investopedia.com/terms/d/donchianchannels.asp

    Args:
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.

    Returns:
        pandas.Series: New feature generated.
    """
    df = pd.DataFrame([close]).transpose()
    df['hband'] = 0.0
    hband = close.rolling(n).max()
    df.loc[close >= hband, 'hband'] = 1.0
    hband = df['hband']
    if fillna:
        hband = hband.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    if is_update:
        return pd.Series(hband, name='dcihband').tail(update_number)
    else:
        return pd.Series(hband, name='dcihband')


def donchian_channel_lband_indicator(close, n=20, fillna=True, is_update=False, update_number=None):
    """Donchian Low Band Indicator

    Returns 1, if close is lower than donchian low band channel. Else, return 0.

    https://www.investopedia.com/terms/d/donchianchannels.asp

    Args:
        close(pandas.Series): dataset 'Close' column.
        n(int): n period.

    Returns:
        pandas.Series: New feature generated.
    """
    df = pd.DataFrame([close]).transpose()
    df['lband'] = 0.0
    lband = close.rolling(n).min()
    df.loc[close <= lband, 'lband'] = 1.0
    lband = df['lband']
    if fillna:
        lband = lband.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    if is_update:
        return pd.Series(lband, name='dcilband').tail(update_number)
    else:
        return pd.Series(lband, name='dcilband')
