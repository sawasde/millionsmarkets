from binance.client import Client
from utils import utils, dynamodb, bintrade
import os

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


@utils.logger.catch
def lambda_launch():
    global COSMOAGENT_CONFIG
    global BIN_CLIENT
    
    print (utils.logger)
    # Load config
    COSMOAGENT_CONFIG = dynamodb.load_feature_value_config(AWS_DYNAMO_SESSION, 'mm_cosmoagent' , DEBUG)

    # Log path
    utils.logger_path(COSMOAGENT_CONFIG['log_path'])

    # Log config
    utils.logger.info(COSMOAGENT_CONFIG)

    #Binance
    utils.logger.info('AUTH BINANCE')
    BIN_CLIENT = Client(BIN_API_KEY, BIN_API_SECRET)

    if DEBUG:
        klines = bintrade.get_chart_data(BIN_CLIENT, 'SOLBUSD', start='1 day ago', end='now', period=BIN_CLIENT.KLINE_INTERVAL_1DAY, df=True, decimal=True)
        print(klines)
