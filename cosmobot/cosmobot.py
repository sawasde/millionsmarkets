""" Cosmo BOT module to send CRYPTO signals calls"""
# pylint: disable=no-name-in-module, import-error

import os
import numpy as np
#import discord
from utils import utils, dynamodb, cosmomixins


#Staging
DEBUG = bool(int(os.getenv('TF_VAR_COSMOBOT_DEBUG')))
FROM_LAMBDA = bool(int(os.getenv('TF_VAR_COSMOBOT_FROM_LAMBDA')))

# Discord vars
DISCORD_COSMOBOT_HOOK_URL = ''
DISCORD_COSMOBOT_ROLE = ''

# AWS Dynamo
AWS_DYNAMO_SESSION = dynamodb.create_session(from_lambda=FROM_LAMBDA)
TABLE_NAME = 'mm_cosmobot'

# General vars
COSMOBOT_CONFIG = {}
SYMBOLS_BASE_PATH = 'cosmobot/assets/'
CSV_ASSET_PATH = '{}{}.csv'
COSMO_SYMBOLS_PARAMETERS = {}
COSMO_SYMBOLS_DFS = {}


@utils.logger.catch
def check_cosmo_call(symbol, mtrend):
    """ Rules to call for a signal """
    # pylint: disable=global-variable-not-assigned

    curr_area = COSMO_SYMBOLS_DFS[symbol]['area'].iloc[-1]
    limit_area = float(COSMO_SYMBOLS_PARAMETERS[symbol]['limit_area'])
    # filter mtrend
    trade = None

    # 1st check: LongTerm trend
    if abs(curr_area) > limit_area:
        utils.logger.info(f'1st check passed curr_area: {curr_area} limit_area: {limit_area}')

        bull_limit_mtrend = int(COSMO_SYMBOLS_PARAMETERS[symbol]['bull_mtrend'])
        bear_limit_mtrend = int(COSMO_SYMBOLS_PARAMETERS[symbol]['bear_mtrend'])

        # 2nd check: mtrend limit reached BUY or SELL
        # BUY
        if mtrend < (bear_limit_mtrend):
            utils.logger.info(f'2nd check passed BUY mtrend: {mtrend}')
            trade = 'BUY'

        # SELL
        if mtrend > (bull_limit_mtrend):
            utils.logger.info(f'2nd check passed SELL mtrend: {mtrend}')
            trade = 'SELL'

    return trade


@utils.logger.catch
def find_peaks(initial_array, order=8888, peak_type='max'):
    """ Find the peaks of an array """

    peaks = []
    arrays = np.array_split(np.flip(initial_array), order)

    if peak_type == 'max':
        for arr in arrays:
            maxi = arr.max()
            if maxi < 0.1:
                continue

            peaks.append(maxi)

    else:
        for arr in arrays:
            mini = arr.min()
            if mini > -0.1:
                continue
            peaks.append(mini)

    return np.array(peaks)


@utils.logger.catch
def update_cosmo_parameters(symbol):
    """ Update dynamo table with current bot data """
    # pylint: disable=global-variable-not-assigned

    global COSMO_SYMBOLS_PARAMETERS
    utils.logger.info('Update cosmo parameters')

    symbol_parameter_item = dynamodb.get_item(  AWS_DYNAMO_SESSION,
                                                TABLE_NAME,
                                                {'feature' : f'{symbol}_parameters'})
    symbol_df = COSMO_SYMBOLS_DFS[symbol]

    # order n
    order_n = int(symbol_parameter_item['order_mtrend'])

    mtrend_array = symbol_df['mtrend'].to_numpy()
    # Find local peaks
    mtrend_maxima = find_peaks(mtrend_array, order=order_n, peak_type='max')
    mtrend_minima = find_peaks(mtrend_array, order=order_n, peak_type='min')

    print('MAXI', mtrend_maxima)
    print('MINI', mtrend_minima)

    maxima_mean = mtrend_maxima.mean()
    minima_mean = mtrend_minima.mean()

    symbol_parameter_item['bull_mtrend']= int(maxima_mean)
    symbol_parameter_item['bear_mtrend'] = int(minima_mean)

    # Update Timestamp
    symbol_parameter_item['timestamp'] = int(utils.get_timestamp(multiplier=1))

    # Log parameters
    utils.logger.info(f'parameters max: {maxima_mean} min {minima_mean}')
    # Put it on memory
    COSMO_SYMBOLS_PARAMETERS[symbol] = symbol_parameter_item

    # Put it on dynamo
    dynamodb.put_item(  AWS_DYNAMO_SESSION,
                        TABLE_NAME,
                        {'feature' : f'{symbol}_parameters',
                        'value' : symbol_parameter_item})


@utils.logger.catch
def update_cosmo_dfs(symbol):
    """ Update local variables with current data """
    # pylint: disable=global-variable-not-assigned

    global COSMO_SYMBOLS_DFS
    utils.logger.info('Update cosmo DFs')

    csv_path = CSV_ASSET_PATH.format(SYMBOLS_BASE_PATH, symbol)
    if FROM_LAMBDA:
        symbol_df = cosmomixins.get_resource_optimized_dfs(AWS_DYNAMO_SESSION,
                                                           symbol, csv_path, 5, 521, False)
    else:
        symbol_df = cosmomixins.get_resource_optimized_dfs(AWS_DYNAMO_SESSION,
                                                           symbol, csv_path, 5, 521, True)

    symbol_df = cosmomixins.aux_format_plotter_df(symbol_df, 31)

    COSMO_SYMBOLS_DFS[symbol] = symbol_df


@utils.logger.catch
def prepare_msg(call, symbol, mtrend, pclose, role):
    """ Prepare Discord message """
    # Prepare message
    msg = f'{call} **{symbol}**\n'
    msg += f'**Cosmo Trend**: {mtrend:.2f}\n'
    msg += f'**Price**: ${pclose:,}\n'
    msg += f'<@&{role}>'
    return msg


@utils.logger.catch
def run():
    """ Routine loop to send message in case of signal """
    # pylint: disable=consider-using-f-string, global-statement, global-variable-not-assigned

    global COSMOBOT_CONFIG

    for symbol in COSMOBOT_CONFIG['crypto_symbols']:

        # Update Stuff
        update_cosmo_dfs(symbol)
        update_cosmo_parameters(symbol)

        # check for a trading call
        symbol_cosmo_info = COSMO_SYMBOLS_DFS[symbol].iloc[-1]
        mtrend = symbol_cosmo_info['mtrend']

        cosmo_call = check_cosmo_call(symbol, mtrend)
        if DEBUG:
            cosmo_call = 'BUY'

        if cosmo_call:
            utils.logger.info(f"Call {cosmo_call} {symbol} sending MSG")
        # Get Cosmo Variables
            pclose = symbol_cosmo_info['pclose']
            area = symbol_cosmo_info['area']
            area = '{:.2e}'.format(area)

            # Prepare message
            msg = prepare_msg(cosmo_call, symbol, mtrend, pclose, DISCORD_COSMOBOT_ROLE)

            if DEBUG:
                utils.logger.info(msg)

            utils.discord_webhhok_send(DISCORD_COSMOBOT_HOOK_URL, 'CosmoBOT', msg)


@utils.logger.catch
def launch(event=None, context=None):
    """ Launch function """
    # pylint: disable=unused-argument, disable=global-statement

    global COSMOBOT_CONFIG
    global DISCORD_COSMOBOT_HOOK_URL
    global DISCORD_COSMOBOT_ROLE

    # Load config
    COSMOBOT_CONFIG = dynamodb.load_feature_value_config(AWS_DYNAMO_SESSION, TABLE_NAME, DEBUG)

    # Log path
    if not FROM_LAMBDA:
        utils.logger_path(COSMOBOT_CONFIG['log_path'])

    # Log discord
    utils.logger.info('Load Discord vars')

    # Discord URL
    if DEBUG:
        DISCORD_COSMOBOT_HOOK_URL = os.environ['TF_VAR_COSMOBOT_DISCORD_HOOK_URL_TEST']
        DISCORD_COSMOBOT_ROLE= os.environ['TF_VAR_COSMOBOT_DISCORD_ROLE_TEST']
    else:
        DISCORD_COSMOBOT_HOOK_URL = os.environ['TF_VAR_COSMOBOT_DISCORD_HOOK_URL']
        DISCORD_COSMOBOT_ROLE = os.environ['TF_VAR_COSMOBOT_DISCORD_ROLE']

    # Run
    run()
