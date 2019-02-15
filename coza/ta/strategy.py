import pandas as pd
from .volatility import bollinger_lband, bollinger_hband


def golden_cross(close,
                 short_win_size=5,
                 long_win_size=20, fillna=True):
    """Moving Average Strategy - Golden Cross

    Args:
        close (pd.Series): Series of the candle data.
        short_win_size (int): window of short-term moving average.
        long_win_size (int): window of long-term moving average.

    Returns:
        bool: decision.
    """
    assert len(close) >= long_win_size and len(close) >= short_win_size, "close(price list) is shorter than win_size(window size)"

    short_mean_curr = close[1:].rolling(window=short_win_size).mean()
    long_mean_curr = close[1:].rolling(window=long_win_size).mean()

    short_mean_last = close[:-1].rolling(window=short_win_size).mean()
    long_mean_last = close[:-1].rolling(window=long_win_size).mean()

    return pd.Series((short_mean_curr > long_mean_curr) & (
                     short_mean_last < long_mean_last),
                     name='gc_%d_%d' % (short_win_size, long_win_size))


def dead_cross(close,
               short_win_size=5,
               long_win_size=20, fillna=True):
    """Moving Average Strategy - Dead Cross

    Args:
        close (pd.Series): Series of the candle data.
        short_win_size (int): window of short-term moving average.
        long_win_size (int): window of long-term moving average.

    Returns:
        bool: decision.
    """

    short_mean_curr = close[1:].rolling(window=short_win_size).mean()
    long_mean_curr = close[1:].rolling(window=long_win_size).mean()

    short_mean_last = close[:-1].rolling(window=short_win_size).mean()
    long_mean_last = close[:-1].rolling(window=long_win_size).mean()

    return pd.Series((short_mean_curr < long_mean_curr) & (
                     short_mean_last > long_mean_last),
                     name='dc_%d_%d' % (short_win_size, long_win_size))


def lower_than_bollinger_lower_bound_rolling(close,
                                             win_size=20,
                                             k=2, fillna=True):
    """Bolinger Band Strategy - Lower bound

    Args:
        close (pd.Series): Series of the candle data.
        win_size (int): window size of bolinger band.
        k (int): bolinger band parameter. a weight of standard deviation.

    Returns:
        pd.Series: decision.
    """
    blb_sr = bollinger_lband(close=close,
                             n=win_size,
                             ndev=k, fillna=fillna)

    return pd.Series(close < blb_sr,
                     name='lower_than_blb_%d_%d' % (win_size, k))


def upper_than_bollinger_upper_bound_rolling(close,
                                             win_size=20,
                                             k=2, fillna=True):
    """Bolinger Band Strategy - Upper bound

    Args:
        close (pd.Series): Series of the candle data.
        win_size (int): window size of bolinger band.
        k (int): bolinger band parameter. a weight of standard deviation.

    Returns:
        pd.Series: decision.
    """
    bub_sr = bollinger_hband(close=close,
                             n=win_size,
                             ndev=k, fillna=fillna)

    return pd.Series(close > bub_sr,
                     name='upper_than_bub_%d_%d' % (win_size, k))



