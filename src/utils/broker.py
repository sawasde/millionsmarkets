""" Binance module to get Crypto data """
# pylint: disable=import-error,no-name-in-module
import os
import pandas as pd
import requests
from utils import utils

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
def yfinance_raw_request(symbol, period='1d', interval='1d', timeout=30):
    """" Sumple Taw request to yahoo finance services """

    data = {}

    url = f'https://query2.finance.yahoo.com/v8/finance/chart/{symbol}'

    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1)'
    user_agent +=  ' AppleWebKit/537.36 (KHTML, like Gecko)'
    user_agent +=  'Chrome/39.0.2171.95 Safari/537.36'

    headers = { 'User-Agent': user_agent}
    params = {'range': period, 'interval': interval}

    response = requests.get(
                        url=url,
                        params=params,
                        headers=headers,
                        timeout=timeout)

    if response.status_code == 200:
        data = response.json()
        data = data['chart']['result'][0]
    else:
        raise RuntimeError(f'Error code: {response.status_code} text: {response.text}')

    return data


@utils.logger.catch
def yfinance_get_chart_data(symbol, period='1d', interval='1d', timeout=30):
    """ Return Symbol Market Data as dataframe """

    new_data = {}

    data = yfinance_raw_request(symbol, period, interval, timeout)
    new_data['timestamp'] = data['timestamp']

    for col_name in ['open', 'high', 'low', 'close', 'volume']:
        new_data[col_name] = data['indicators']['quote'][0][col_name]

    df_result = pd.DataFrame.from_dict(new_data)
    return df_result


@utils.logger.catch
def us_market_status():
    """ Check US market Status """

    # Check for market hours
    if not us_market_time():
        return False

    # Check for holidays
    data = yfinance_raw_request('%5EDJI')
    now_tms = data['timestamp'][-1]
    diff_tms = utils.date_ago_timestmp(minutes=4)

    if now_tms > diff_tms:
        return True

    return False

@utils.logger.catch
def us_market_time():
    """ return True if we're in stock market hours """

    now = utils.date_now(use_tuple=True, tmz='US/Eastern')
    # y, m, d, h, minute, sec, wd, yd, i
    hour = now[3]
    minute = now[4]
    wday = now[6]

    if 0 <= wday <= 4:
        # US stock open close hours
        if hour < 9 or hour >= 16:
            return False
        # US stock ensure starting at 9:30 am
        if hour == 9 and minute < 30:
            return False

        return True

    return False
