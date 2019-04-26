from datetime import datetime, timedelta

import numpy as np
import pytz
import math


KST = pytz.timezone('Asia/Seoul')


def pick_from_candle(candle_list, pick='close'):
    """Transform candle API result

    Args:
        candle_list (list): list of dict, coin candle data.
        pick (str): 'close', 'open', 'low', 'high', 'volume', 'timestamp'

    Returns:
        list, list of value
    """
    k = {'close': 'c',
         'open': 'o',
         'low': 'l',
         'high': 'high',
         'volume': 'v',
         'timestamp': 't'}

    return [candle[k[pick]] for candle in candle_list]


# ======================================
# pseudo data generator

def generate_pseudo_periodic_data(X, a, b, k_1, t_1, k_2, t_2, p, sigma):
    """Generate psuedo periodic data.
    ax + b + k*sin(X* 2 * PI / t) + p*N(0, sigma)

    Args:
        X (np.array): 1-D array.
        a (float): coefficient of linear part.
        b (float): bias.
        k_1 (float): coefficient of short term sin function.
        t_1 (float): period of short term sin function.
        k_2 (float): coefficient of long term sin function.
        t_2 (float): period of long term sin function.
        p (float): coefficient of gaussian noise part.

    Returns:
        np.array: value of this functions.

    """

    radian_unit_1 = 2*np.pi / t_1
    small_sin_val = k_1*np.sin(X*radian_unit_1)

    radian_unit_2 = 2*np.pi / t_2
    big_sin_val = k_2*np.sin(X*radian_unit_2)

    linear_val = X * a + b
    gaussian_noise = p * np.random.normal(loc=0., scale=1., size=len(X))

    Y = small_sin_val + big_sin_val + linear_val + gaussian_noise
    return Y


def truncate(f, n):
    return math.floor(round(f * 10 ** n, n)) / 10 ** n


def get_midnight(dt):
    return datetime.combine(dt.date(), datetime.min.time(), dt.tzinfo)


def align_date(date, interval):
    """
    주어진 datetime을 interval(분)에 따른 가장 최근의 datetime으로 정렬한다.
    ex) 13:37의 경우
        interval=5      -> 13:35
        interval=15     -> 13:30
        interval=30     -> 13:30
        interval=60     -> 13:00
        interval=120    -> 12:00
    :param date: datetime
    :param interval: 간격(int)
    :return: datetime
    """
    delta = (date - get_midnight(date)).total_seconds() % (interval * 60)
    return date - timedelta(seconds=delta)


def now(exchange=None, rounding_seconds=False):
    TZ_TABLE = {
        'coinone': KST,
        'upbit': KST,
    }

    if rounding_seconds:
        dt = datetime.now(TZ_TABLE.get(exchange.lower(), KST)).replace(second=0, microsecond=0)
    else:
        dt = datetime.now(TZ_TABLE.get(exchange.lower(), KST))
    return dt


