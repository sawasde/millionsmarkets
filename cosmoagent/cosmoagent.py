""" Cosmoagent module for cryptocurrencies """
# pylint: disable=no-name-in-module, import-error

import os
import json
from decimal import Decimal
from binance.client import Client

# local imports
from utils import utils, trends, bintrade, dynamodb
from utils import cosmomixins

#Staging
DEBUG = bool(int(os.getenv('COSMOBOT_DEBUG')))
FROM_LAMBDA = bool(int(os.getenv('COSMOBOT_FROM_LAMBDA')))

# Binance variables
BIN_API_KEY = os.environ['BIN_API_KEY']
BIN_API_SECRET = os.environ['BIN_API_SECRET']
BIN_CLIENT = None
ALL_CRYPTO_PRICE = []

# AWS Dynamo
AWS_DYNAMO_SESSION = dynamodb.create_session(from_lambda=FROM_LAMBDA)

# General vars
COSMOAGENT_CONFIG = {}


@utils.logger.catch
def put_planet_trend_info(symbol, ptrend, mtrend, strend, pd_limit, pz_limit, pclose):
    """ Put planet trend indicator in Dynamo table """
    # pylint: disable=too-many-arguments

    cosmo_time = cosmomixins.get_cosmobot_time()
    cosmo_week = cosmo_time[0]
    cosmo_timestamp = cosmo_time[4]


    to_put = {  'week' : cosmo_week,
                'timestamp' : cosmo_timestamp,
                'ptrend' : ptrend,
                'mtrend' : mtrend,
                'strend' : strend,
                'pclose' : pclose,
                'pd_limit' : pd_limit,
                'pz_limit' : pz_limit }

    item = json.loads(json.dumps(to_put), parse_float=Decimal)

    if DEBUG:
        dynamodb.put_item(  AWS_DYNAMO_SESSION,
                            f'mm_cosmobot_historical_{symbol}_test',
                            item,
                            region='sa-east-1')
    else:
        dynamodb.put_item(  AWS_DYNAMO_SESSION,
                            f'mm_cosmobot_historical_{symbol}',
                            item,
                            region='sa-east-1')



def get_planet_trend(symbol, bin_client=BIN_CLIENT):
    """ Get planet trend indicator data """
    # pylint: disable=broad-exception-caught, invalid-name

    utils.logger.info(f'Get Planet info for {symbol}')

    try:

        # 1day data
        trend_data = bintrade.get_chart_data(   bin_client,
                                                symbol,
                                                start='44 days ago',
                                                end='now',
                                                period=bin_client.KLINE_INTERVAL_1DAY,
                                                df=True,
                                                decimal=True)

        ptrend, pclose, pd_limit, pz_limit = trends.planets_volume(trend_data)
        minfo = trends.planets_volume(trend_data, trend_type='mean')
        sinfo = trends.planets_volume(trend_data, trend_type='sum')

        return (symbol, ptrend, minfo[0], sinfo[0], pd_limit, pz_limit, pclose)

    except Exception as e:
        utils.logger.error(e)
        return (symbol, None, None, None, None, None, None)



@utils.logger.catch
def run():
    """ Run cosmoagent"""
    # pylint: disable=global-statement
    global ALL_CRYPTO_PRICE
    global COSMOAGENT_CONFIG

	# Get all crypto assets price
    ALL_CRYPTO_PRICE = BIN_CLIENT.get_all_tickers()

	# Load config in loop
    COSMOAGENT_CONFIG = dynamodb.load_feature_value_config( AWS_DYNAMO_SESSION,
                                                            'mm_cosmoagent',
                                                            DEBUG)

    # loop crypto
    for symbol in COSMOAGENT_CONFIG['crypto_symbols']:

        symbol_cosmos_info = get_planet_trend(symbol, BIN_CLIENT)

        if symbol_cosmos_info[1]:
            put_planet_trend_info(*symbol_cosmos_info)
        else:
            continue


@utils.logger.catch
def launch(event=None, context=None):
    """ Load configs and run once the agent"""
    # pylint: disable=unused-argument, global-statement

    global COSMOAGENT_CONFIG
    global BIN_CLIENT

    print (utils.logger)
    # Load config
    COSMOAGENT_CONFIG = dynamodb.load_feature_value_config( AWS_DYNAMO_SESSION,
                                                            'mm_cosmoagent' ,
                                                            DEBUG)

    # Log path
    if not FROM_LAMBDA:
        utils.logger_path(COSMOAGENT_CONFIG['log_path'])

    # Log config
    utils.logger.info(COSMOAGENT_CONFIG)

    # Binance
    utils.logger.info('AUTH BINANCE')
    BIN_CLIENT = Client(BIN_API_KEY, BIN_API_SECRET)

    if DEBUG:
        klines = bintrade.get_chart_data(BIN_CLIENT,
                                        'SOLBUSD',
                                        start='1 day ago',
                                        end='now',
                                        period=BIN_CLIENT.KLINE_INTERVAL_1DAY,
                                        df=True,
                                        decimal=True)
        print(klines)

    # Start bot
    run()
