""" Binance module to get Crypto data """
# pylint: disable=no-name-in-module, import-error
import pandas as pd
import yfinance as yf
from utils import utils


@utils.logger.catch
def get_chart_data(symbol, period='1d', interval='1d'):
    """ Return Symbol Market Data as dataframe """

    data = yf.download(symbol, period=period, interval=interval, progress=False)
    data = data.reset_index()
    data.columns= data.columns.str.lower()
    data = data[['date', 'open', 'close', 'high', 'low', 'volume']]

    return data
