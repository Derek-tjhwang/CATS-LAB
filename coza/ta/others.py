# -*- coding: utf-8 -*-
"""
.. module:: others
   :synopsis: Others Indicators.

.. moduleauthor:: Dario Lopez Padial (Bukosabino)

"""
import pandas as pd


def daily_return(close, fillna=True, is_update=False, update_number=None):
    """Daily Return (DR)

    Args:
        close(pandas.Series): dataset 'Close' column.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.
    """
    dr = (close / close.shift(1)) - 1
    dr *= 100
    if fillna:
        dr = dr.fillna(0)
        
    if is_update:
        return pd.Series(dr, name='d_ret').tail(update_number)
    else:
        return pd.Series(dr, name='d_ret')


def cumulative_return(close, fillna=True, is_update=False, update_number=None):
    """Cumulative Return (CR)

    Args:
        close(pandas.Series): dataset 'Close' column.
        fillna(bool): if True, fill nan values.

    Returns:
        pandas.Series: New feature generated.
    """
    cr = (close / close.iloc[0]) - 1
    cr *= 100
    if fillna:
        cr = cr.fillna(method='backfill')
    
    if is_update:
        return pd.Series(cr, name='cum_ret').tail(update_number)
    else:
        return pd.Series(cr, name='cum_ret')
