""" Cosmo Symbols """
# pylint: disable=no-name-in-module, import-error

import os
import time
import threading
# local imports
from utils import utils, dynamodb, cosmomixins


# AWS Dynamo
STAGING = bool(int(os.getenv('TF_VAR_STAGING')))
AWS_DYNAMO_SESSION = dynamodb.create_session()

if STAGING:
    CONFIG_TABLE_NAMES =  {'cosmobot' : 'mm_cosmobot_staging',
                            'cosmoagent' : 'mm_cosmoagent_staging'}
else:
    CONFIG_TABLE_NAMES = {'cosmobot' : 'mm_cosmobot',
                            'cosmoagent' : 'mm_cosmoagent'}

# Cosmosymbols vars
COSMOBOT_CONFIG = {}
COSMOAGENT_CONFIG = {}
CHART_BASE_PATH = 'assets/'
SYMBOL_TYPE = os.getenv('TF_VAR_SYMBOL_TYPE')
US_MARKET_STATUS = True


@utils.logger.catch
def compare_symbols():
    """ Compare which symbols are in whic bot"""

    ca_symbols = COSMOAGENT_CONFIG[f'{SYMBOL_TYPE.lower()}_symbols']
    cb_symbols = COSMOBOT_CONFIG[f'{SYMBOL_TYPE.lower()}_symbols']

    utils.logger.info(f'{SYMBOL_TYPE} Cosmoagent Total: {len(ca_symbols)}')
    utils.logger.info(f'{SYMBOL_TYPE} Cosmobot Total: {len(cb_symbols)}')

    missing_cb_symbols = [sym for sym  in ca_symbols if sym  not in cb_symbols]

    utils.logger.info(f'{SYMBOL_TYPE} Cosmobot missing: {missing_cb_symbols}')

    return missing_cb_symbols


@utils.logger.catch
def get_cb_migrate_symbols(missing_cb_symbols):
    """ Get all possible symbols to migrate"""
    symbols_to_migrate = []
    for symbol in missing_cb_symbols:

        csv_path = f'{CHART_BASE_PATH}{SYMBOL_TYPE}/{symbol}.csv'
        df_result = cosmomixins.get_resource_optimized_dfs( AWS_DYNAMO_SESSION,
                                                            symbol,
                                                            csv_path,
                                                            5,
                                                            521,
                                                            True,
                                                            STAGING,
                                                            True)
        symbol_df_len = len(df_result)
        utils.logger.info(f'{SYMBOL_TYPE} {symbol} length: {symbol_df_len}')

        if symbol_df_len > cosmomixins.MIN_DF_LEN:
            symbols_to_migrate.append(symbol)

    utils.logger.info(f'{SYMBOL_TYPE} Cosmobot to_migrate: {symbols_to_migrate}')

    return symbols_to_migrate


@utils.logger.catch
def update_cb_symbols(symbols_to_migrate):
    """ Create Parameters Table and add symbol to the config"""

    if SYMBOL_TYPE == 'STOCK':
        template_table = 'EXTO_parameters'

    elif SYMBOL_TYPE == 'ETF':
        template_table = 'TLT_parameters'
    else:
        #CRYPTO
        template_table = 'BNBUSDT_parameters'

    for symbol in symbols_to_migrate:

        # Create Parameters table
        utils.logger.info(f'{SYMBOL_TYPE} {symbol} Update parameters table')
        symbol_parameter_item = dynamodb.get_item(  AWS_DYNAMO_SESSION,
                                                    CONFIG_TABLE_NAMES['cosmobot'],
                                                    {'feature' : template_table})

        to_put = {'feature' : f'{symbol}_parameters','value' : symbol_parameter_item}

        dynamodb.put_item_from_dict(AWS_DYNAMO_SESSION,
                                    CONFIG_TABLE_NAMES['cosmobot'],
                                    to_put,
                                    STAGING)

    # Update Symbols in config table
    utils.logger.info(f'{SYMBOL_TYPE} Update config table')

    cosmobot_config = dict(COSMOBOT_CONFIG)
    cosmobot_config[f'{SYMBOL_TYPE.lower()}_symbols'] += symbols_to_migrate

    to_put = {'feature' : 'config', 'value' : cosmobot_config}

    dynamodb.put_item_from_dict(AWS_DYNAMO_SESSION,
                                CONFIG_TABLE_NAMES['cosmobot'],
                                to_put,
                                STAGING)


@utils.logger.catch
def launch():
    """ Launch function """
    # pylint: disable=global-statement
    global COSMOBOT_CONFIG, COSMOAGENT_CONFIG, US_MARKET_STATUS

    # Load config
    COSMOBOT_CONFIG = dynamodb.load_feature_value_config(AWS_DYNAMO_SESSION,
                                                         CONFIG_TABLE_NAMES['cosmobot'])
    COSMOAGENT_CONFIG = dynamodb.load_feature_value_config(AWS_DYNAMO_SESSION,
                                                           CONFIG_TABLE_NAMES['cosmoagent'])

    missing_cb_symbols = compare_symbols()

    cb_symbols_to_migrate = get_cb_migrate_symbols(missing_cb_symbols)

    update_cb_symbols(cb_symbols_to_migrate)
