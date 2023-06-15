""" Cosmoagent module for cryptocurrencies """
# pylint: disable=no-name-in-module, import-error, R0801

import os
import json
import time
import threading
from decimal import Decimal

# local imports
from utils import utils, trends, broker, dynamodb
from utils import cosmomixins

# Staging
STAGING = bool(int(os.getenv('TF_VAR_STAGING')))

# Cosmoagent vars
FROM_LAMBDA = bool(int(os.getenv('TF_VAR_FROM_LAMBDA')))
SYMBOL_TYPE = os.getenv('TF_VAR_SYMBOL_TYPE')

# AWS Dynamo
AWS_DYNAMO_SESSION = dynamodb.create_session(from_lambda=FROM_LAMBDA)
if STAGING:
    CONFIG_TABLE_NAME = 'mm_cosmoagent_staging'
else:
    CONFIG_TABLE_NAME = 'mm_cosmoagent'


@utils.logger.catch
def put_planet_trend_info(symbol, ptrend, mtrend, strend, pd_limit, pz_limit, pclose):
    """ Put planet trend indicator in Dynamo table """
    # pylint: disable=too-many-arguments

    utils.logger.info(f'{symbol} Put Planet info')

    cosmo_time = cosmomixins.get_cosmobot_time()
    cosmo_week = cosmo_time[0]
    cosmo_timestamp = cosmo_time[4]

    to_log = f'{symbol} pclose: {pclose} tms: {cosmo_timestamp} mtrend: {mtrend}'
    utils.logger.info(to_log)

    to_put = {  'week' : cosmo_week,
                'timestamp' : cosmo_timestamp,
                'ptrend' : ptrend,
                'mtrend' : mtrend,
                'strend' : strend,
                'pclose' : pclose,
                'pd_limit' : pd_limit,
                'pz_limit' : pz_limit }

    item = json.loads(json.dumps(to_put), parse_float=Decimal)
    table_name = f'mm_cosmobot_historical_{symbol}'

    if STAGING:
        table_name += '_staging'

    dynamodb.put_item(  AWS_DYNAMO_SESSION,
                        table_name,
                        item,
                        region='sa-east-1')



def get_crypto_planet_trend(symbol):
    """ Get planet trend indicator data """
    # pylint: disable=broad-exception-caught
    utils.logger.info(f'{symbol} Get Planet info')

    try:

        # 1day data
        trend_data = broker.binance_get_chart_data( symbol,
                                                    start='44 days ago',
                                                    end='now',
                                                    period='1d',
                                                    is_df=True,
                                                    decimal=True)

        ptrend, pclose, pd_limit, pz_limit = trends.planets_volume(trend_data)
        minfo = trends.planets_volume(trend_data, trend_type='mean')
        sinfo = trends.planets_volume(trend_data, trend_type='sum')

        return (symbol, ptrend, minfo[0], sinfo[0], pd_limit, pz_limit, pclose)

    except Exception as exc:
        utils.logger.error(exc)
        return (symbol, None, None, None, None, None, None)


def get_stock_planet_trend(symbol):
    """ Get planet trend indicator data """
    # pylint: disable=broad-exception-caught
    utils.logger.info(f'Get Planet info for {symbol}')

    try:

        # 1day data
        trend_data = broker.yfinance_get_chart_data( symbol, period='30d', interval='1d')

        ptrend, pclose, pd_limit, pz_limit = trends.planets_volume(trend_data)
        minfo = trends.planets_volume(trend_data, trend_type='mean')
        sinfo = trends.planets_volume(trend_data, trend_type='sum')

        return (symbol, ptrend, minfo[0], sinfo[0], pd_limit, pz_limit, pclose)

    except Exception as exc:
        utils.logger.error(exc)
        return (symbol, None, None, None, None, None, None)


@utils.logger.catch
def run(symbol):
    """ Run cosmoagent"""

    utils.logger.info(f'Run Cosmoagent for {symbol}')

    if SYMBOL_TYPE == 'CRYPTO':
        symbol_cosmos_info = get_crypto_planet_trend(symbol)
    elif SYMBOL_TYPE == 'STOCK':
        symbol_cosmos_info = get_stock_planet_trend(symbol)
    else:
        symbol_cosmos_info = (None,)

    if symbol_cosmos_info[1]:
        put_planet_trend_info(*symbol_cosmos_info)


@utils.logger.catch
def launch(event=None, context=None):
    """ Load configs and run once the agent"""
    # pylint: disable=unused-argument, global-statement

    # Load config
    cosmoagent_config = dynamodb.load_feature_value_config( AWS_DYNAMO_SESSION,
                                                            CONFIG_TABLE_NAME)

    # Log path
    if not FROM_LAMBDA:
        utils.logger_path(cosmoagent_config['log_path'])

    # Start bot run() with threads
    threads = []

    if SYMBOL_TYPE == 'CRYPTO':
        # Use threading but be careful to not impact binance rate limit: max 20 req/s
        symbols_chunks = utils.divide_list_chunks(cosmoagent_config['crypto_symbols'], 10)

    elif SYMBOL_TYPE == 'STOCK' and utils.is_stock_market_hours():
        symbols_chunks = utils.divide_list_chunks(cosmoagent_config['stock_symbols'], 10)

    else:
        if not utils.is_stock_market_hours():
            utils.logger.info('US Market close')
        else:
            utils.logger.error(f'Wrong Symbol Type: {SYMBOL_TYPE}')
        symbols_chunks = []

    for chunk in symbols_chunks:
        for symbol in chunk:
            runner = threading.Thread(target=run, args=(symbol,))
            threads.append(runner)
            runner.start()

        for thread in threads:
            thread.join()

        time.sleep(2)
