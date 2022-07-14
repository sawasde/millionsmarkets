from twisted.internet import task, reactor
import pandas as pd
from loguru import logger
from binance.client import Client
from decimal import Decimal
import os
import json

# local imports
from utils import utils, trends, bintrade, dynamodb


#Staging
DEBUG = bool(int(os.getenv('COSMOBOT_DEBUG')))

# Binance variables
BIN_API_KEY = os.environ['BIN_API_KEY']
BIN_API_SECRET = os.environ['BIN_API_SECRET']
BIN_CLIENT = None
ALL_CRYPTO_PRICE = []

# AWS Dynamo
AWS_DYNAMO_SESSION = dynamodb.create_session()

# General vars
COSMOAGENT_CONFIG = {}


@logger.catch
def load_config():
    logger.info(f'Load Config dict')
   
    if DEBUG:
        return dynamodb.get_item(AWS_DYNAMO_SESSION, 'mm_cosmoagent', {'feature' : 'test_config'})
    else:
        return dynamodb.get_item(AWS_DYNAMO_SESSION, 'mm_cosmoagent', {'feature' : 'prod_config'})



@utils.logger.catch
def put_planet_trend_info(symbol, ptrend, mtrend, strend, pd_limit, pz_limit, pclose, binplotter=False, pclose_limit_ft=False):


    timestamp = int(utils.get_timestamp(multiplier=1))
    date = utils.timestamp_to_date(timestamp)
    week = date.isocalendar()[1]
    year = date.isocalendar()[0]
    iweek = f'{year}_{week}'
    to_put = {  'week' : iweek, 
                'timestamp' : timestamp,
                'ptrend' : ptrend,
                'mtrend' : mtrend,
                'strend' : strend,
                'pclose' : pclose,
                'pd_limit' : pd_limit,
                'pz_limit' : pz_limit }

    item = json.loads(json.dumps(to_put), parse_float=Decimal)

    if DEBUG:
        dynamodb.put_item(AWS_DYNAMO_SESSION, f'mm_cosmobot_historical_{symbol}_test', item)
    else:
        dynamodb.put_item(AWS_DYNAMO_SESSION, f'mm_cosmobot_historical_{symbol}', item)


@utils.logger.catch
def get_planet_trend(symbol):


    # 1day data
    trend_data = bintrade.get_chart_data(BIN_CLIENT, symbol, start='44 days ago', end='now', period=BIN_CLIENT.KLINE_INTERVAL_1DAY, df=True, decimal=True)
    ptrend, pclose, pd_limit, pz_limit = trends.planets_volume(trend_data)
    mtrend, mclose, md_limit, mz_limit = trends.planets_volume(trend_data, trend_type='mean')
    strend, sclose, sd_limit, mz_limit = trends.planets_volume(trend_data, trend_type='sum')
    
    # Execute
    put_planet_trend_info(symbol, ptrend, mtrend, strend, pd_limit, pz_limit, pclose)



@utils.logger.catch
def loop():
    global ALL_CRYPTO_PRICE
    global COSMOAGENT_CONFIG

	# Get all crypto assets price
    ALL_CRYPTO_PRICE = BIN_CLIENT.get_all_tickers()

	# Load config in loop
    COSMOAGENT_CONFIG = load_config()

    # loop crypto
    for symbol in COSMOAGENT_CONFIG['crypto_symbols']:
        get_planet_trend(symbol)


@logger.catch
def launch():
    global COSMOAGENT_CONFIG
    global BIN_CLIENT
    
    # Load config
    COSMOAGENT_CONFIG = load_config()

    # Log path
    logger.add(COSMOAGENT_CONFIG['log_path'])

    # Log config
    logger.info(COSMOAGENT_CONFIG)

    #Binance
    logger.info('AUTH BINANCE')
    BIN_CLIENT = Client(BIN_API_KEY, BIN_API_SECRET)

    if DEBUG:
        klines = bintrade.get_chart_data(BIN_CLIENT, 'SOLBUSD', start='1 day ago', end='now', period=BIN_CLIENT.KLINE_INTERVAL_1DAY, df=True, decimal=True)
        print(klines)

    loop_timeout = int(COSMOAGENT_CONFIG['loop_timeout'])
    loop_call = task.LoopingCall(loop)
    loop_call.start(loop_timeout)
    reactor.run()
    