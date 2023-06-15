""" Binance module to get Crypto data """
# pylint: disable=import-error,no-name-in-module
import os
import pandas as pd
from utils import utils

SYMBOL_TYPE = os.getenv('TF_VAR_SYMBOL_TYPE')

if SYMBOL_TYPE == 'CRYPTO':
    from binance.client import Client as binanceClient

elif SYMBOL_TYPE == 'STOCK':
    import yfinance as yf
else:
    utils.logger.error('WRONG SYMBOL')

@utils.logger.catch
def binance_get_price_by_symbol(all_crypto_price, symbol='BTCBUSD'):
    """ Get the current price of symbol """

    for sym_dic in all_crypto_price:

        if sym_dic['symbol'] == symbol:
            return float(sym_dic['price'])

    return 0.0


@utils.logger.catch
def binance_get_spot_balance(bin_client):
    """ Get the current Spot balance """

    info = bin_client.get_account()
    balances = info['balances']
    free_total = 0.0
    locked_total = 0.0

    for item in balances:
        sym = item['asset']
        free = float(item['free'])
        locked = float(item['locked'])

        print(sym, free, locked)

        free_total += free * binance_get_price_by_symbol(sym+'BUSD')
        locked_total += locked * binance_get_price_by_symbol(sym+'BUSD')

    return (free_total, locked_total)


@utils.logger.catch
def binance_get_chart_data(symbol, start='', end='', period=None,
                                is_df=True, decimal=True, ohclv=True):
    """ Return Symbol Market Data as list or dataframe """
    # pylint: disable=too-many-arguments

    bin_api_key = os.getenv('TF_VAR_BIN_API_KEY')
    bin_api_secret = os.getenv('TF_VAR_BIN_API_SECRET')
    bin_client = binanceClient(bin_api_key, bin_api_secret)

    if period == '1d':
        period = bin_client.KLINE_INTERVAL_1DAY

    data = bin_client.get_historical_klines(symbol, period, start, end)

    if is_df:
        data = pd.DataFrame(data).astype(float)
        data.columns = ['date' , 'open', 'high', 'low', 'close', 'volume',
                                'ctms', 'qav', 'not', 'tbbav', 'tbqasv', 'i']

        data.date = data.date.astype(int)

        if not decimal:
            data = data.apply(lambda x:
                              x*pow(10,8) if x.name in ['open', 'high', 'low', 'close'] else x)

    if ohclv:
        data = data[['date', 'open', 'close', 'high', 'low', 'volume']]

    return data


@utils.logger.catch
def yfinance_get_chart_data(symbol, period='1d', interval='1d'):
    """ Return Symbol Market Data as dataframe """

    data = yf.download(symbol, period=period, interval=interval, progress=False)
    data = data.reset_index()
    data.columns= data.columns.str.lower()
    data = data[['date', 'open', 'close', 'high', 'low', 'volume']]

    return data
