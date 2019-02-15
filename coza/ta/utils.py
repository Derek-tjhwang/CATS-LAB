# -*- coding: utf-8 -*-
import math
import pandas as pd


def dropna(df):
    """Drop rows with "Nans" values
    """
    df = df[df < math.exp(709)] # big number
    df = df[df != 0.0]
    df = df.dropna()
    return df


def ema(series, periods, fillna=True):
    if fillna:
        return series.ewm(span=periods, min_periods=0).mean()
    return series.ewm(span=periods, min_periods=periods).mean()


def candle_slicing(df, n, update_number):
    """
        Args:
            df (pd.DataFrame) : dataframe
            n (int) : timeframe
            update_number (int) : number of update
        
        return: df (pd.DataFrame) : candles which need to update
    """
    
    return df.tail(n + update_number - 1)