""" Cosmo BOT module to send CRYPTO signals calls"""
# pylint: disable=no-name-in-module, import-error, R0801

import os
import json
from decimal import Decimal
import numpy as np
import pandas as pd
#import discord
from utils import utils, dynamodb, cosmomixins


#Staging
STAGING = bool(int(os.getenv('TF_VAR_COSMOBOT_STAGING')))
FROM_LAMBDA = bool(int(os.getenv('TF_VAR_COSMOBOT_FROM_LAMBDA')))

# Discord vars
DISCORD_COSMOBOT_HOOK_URL = os.environ['TF_VAR_COSMOBOT_DISCORD_HOOK_URL']
DISCORD_COSMOBOT_ROLE = os.environ['TF_VAR_COSMOBOT_DISCORD_ROLE']

# AWS Dynamo
AWS_DYNAMO_SESSION = dynamodb.create_session(from_lambda=FROM_LAMBDA)

if STAGING:
    TABLE_NAME = 'mm_cosmobot_staging'
else:
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

    utils.logger.info(f'MAX Peaks {mtrend_maxima}')
    utils.logger.info(f'MIN Peaks {mtrend_minima}')

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
                                                           symbol, csv_path, 5, 521, False, STAGING)
    else:
        symbol_df = cosmomixins.get_resource_optimized_dfs(AWS_DYNAMO_SESSION,
                                                           symbol, csv_path, 5, 521, True, STAGING)

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
def check_last_calls(symbol, cosmo_call, mtrend, cosmo_time):
    """ Check last calls and compare to the current call to filter it """

    utils.logger.info(f'{symbol} Checking last calls')
    table_name = 'mm_cosmobot_calls'
    week = cosmo_time[0]
    timestamp = utils.date_ago_timestmp(days=1)

    if STAGING:
        table_name += '_staging'

    info = dynamodb.query_items(dyn_session=AWS_DYNAMO_SESSION,
                                table_name=table_name,
                                pkey='week',
                                pvalue=week,
                                query_type='both',
                                skey='timestamp',
                                svalue=timestamp,
                                scond='gte',
                                region='sa-east-1')

    if len(info) == 0:
        return True

    last_call = cosmomixins.aux_format_dynamo_df(pd.DataFrame(info))
    mask = (last_call['symbol'] == symbol) & (last_call['cosmo_call'] == cosmo_call)
    filter_call = last_call[mask]

    if len(filter_call) == 0:
        return True

    lc_mtrend = filter_call['mtrend'].iloc[-1]

    utils.logger.info(f'{symbol} mtrends last call: {lc_mtrend} current: {mtrend}')
    new_mtrend = abs(lc_mtrend) * float(COSMOBOT_CONFIG['mtrend_factor'])
    utils.logger.info(f'New mtrend {new_mtrend}')

    if  abs(mtrend) > new_mtrend:
        return False

    return True


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

        if cosmo_call:
            # Get Cosmo Time Variables
            cosmo_time = cosmomixins.get_cosmobot_time()

            if check_last_calls(symbol, cosmo_call, mtrend, cosmo_time):

                utils.logger.info(f"Call {cosmo_call} {symbol} sending MSG")
                # Get Cosmo Variables
                pclose = symbol_cosmo_info['pclose']
                ptrend = symbol_cosmo_info['ptrend']
                strend = symbol_cosmo_info['strend']
                pd_limit = symbol_cosmo_info['pd_limit']
                pz_limit = symbol_cosmo_info['pz_limit']
                area = symbol_cosmo_info['area']
                area = '{:.2e}'.format(area)



                # Prepare message
                msg = prepare_msg(cosmo_call, symbol, mtrend, pclose, DISCORD_COSMOBOT_ROLE)

                if STAGING:
                    utils.logger.info(msg)

                utils.discord_webhhok_send(DISCORD_COSMOBOT_HOOK_URL, 'CosmoBOT', msg)

                to_put = {  'week' : cosmo_time[0],
                            'timestamp' : cosmo_time[4],
                            'cosmo_call' : cosmo_call,
                            'symbol' : symbol,
                            'mtrend' : mtrend,
                            'area'   : area,
                            'strend' : strend,
                            'ptrend' : ptrend,
                            'pclose' : pclose,
                            'pz_limit' : pz_limit,
                            'pd_limit' : pd_limit }

                item = json.loads(json.dumps(to_put), parse_float=Decimal)
                table_name = 'mm_cosmobot_calls'

                if STAGING:
                    table_name += '_staging'


                dynamodb.put_item(  AWS_DYNAMO_SESSION,
                                    table_name,
                                    item,
                                    region='sa-east-1')


@utils.logger.catch
def launch(event=None, context=None):
    """ Launch function """
    # pylint: disable=unused-argument, global-statement

    global COSMOBOT_CONFIG

    # Load config
    COSMOBOT_CONFIG = dynamodb.load_feature_value_config(   AWS_DYNAMO_SESSION,
                                                            TABLE_NAME)

    # Log path
    if not FROM_LAMBDA:
        utils.logger_path(COSMOBOT_CONFIG['log_path'])

    # Log discord
    utils.logger.info('Load Discord vars')

    # Run
    run()
