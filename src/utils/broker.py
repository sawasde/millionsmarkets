""" Binance module to get Crypto data """
# pylint: disable=import-error,no-name-in-module
import os
import pandas as pd
import requests
from src.utils import utils

SYMBOL_TYPE = os.getenv('TF_VAR_SYMBOL_TYPE')

if SYMBOL_TYPE == 'CRYPTO':
    from binance.client import Client as binanceClient


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
    else:
        period = bin_client.KLINE_INTERVAL_15MINUTE

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
def yfinance_get_chart_data(symbol, period='1d', interval='1d', timeout=30):
    """ Return Symbol Market Data as dataframe """

    new_data = {}
    url = f'https://query2.finance.yahoo.com/v8/finance/chart/{symbol}'

    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1)'
    user_agent +=  ' AppleWebKit/537.36 (KHTML, like Gecko)'
    user_agent +=  'Chrome/39.0.2171.95 Safari/537.36'

    headers = { 'User-Agent': user_agent}
    params = {'range': period, 'interval': interval}

    response = requests.get(
                        url=url,
                        params=params,
                        timeout=timeout,
                        headers=headers)

    if response.status_code == 200:
        data = response.json()
    else:
        raise RuntimeError(f'Error code: {response.status_code} text: {response.text}')

    data = data['chart']['result'][0]
    new_data['timestamp'] = data['timestamp']

    for col_name in ['open', 'high', 'low', 'close', 'volume']:
        new_data[col_name] = data['indicators']['quote'][0][col_name]

    df_result = pd.DataFrame.from_dict(new_data)
    return df_result
