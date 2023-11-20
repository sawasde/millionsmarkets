""" Cosmo BOT module to send CRYPTO signals calls"""
# pylint: disable=no-name-in-module, import-error, R0801

import os
import threading
from decimal import Decimal
import yfinance as yf
import numpy as np
import pandas as pd
#import discord
from utils import utils, dynamodb, cosmomixins, broker


#Staging
STAGING = bool(int(os.getenv('TF_VAR_STAGING')))
FROM_LAMBDA = bool(int(os.getenv('TF_VAR_FROM_LAMBDA')))

# Discord vars
DISCORD_COSMOBOT_ROLE = os.getenv('TF_VAR_COSMOBOT_DISCORD_ROLE')
DISCORD_COSMOBOT_HOOK_URL = ""

# AWS Dynamo
AWS_DYNAMO_SESSION = dynamodb.create_session(from_lambda=FROM_LAMBDA)

if STAGING:
    CONFIG_TABLE_NAME = 'mm_cosmobot_staging'
else:
    CONFIG_TABLE_NAME = 'mm_cosmobot'

# cosmobot vars
COSMOBOT_CONFIG = {}
CHART_BASE_PATH = 'assets/'
COSMO_SYMBOLS_PARAMETERS = {}
COSMO_SYMBOLS_DFS = {}
SYMBOL_TYPE = os.getenv('TF_VAR_SYMBOL_TYPE')
US_MARKET_STATUS = True

@utils.logger.catch
def check_cosmo_call(symbol, mtrend):
    """ Rules to call for a signal """
    # pylint: disable=global-variable-not-assigned, line-too-long

    if len(COSMO_SYMBOLS_DFS[symbol]) < cosmomixins.MIN_DF_LEN:
        return None

    curr_area = COSMO_SYMBOLS_DFS[symbol]['area'].iloc[-1]
    limit_area = float(COSMO_SYMBOLS_PARAMETERS[symbol]['limit_area'])
    # filter mtrend
    trade = None

    # 1st check: LongTerm trend
    if abs(curr_area) > limit_area:
        utils.logger.info(f'{symbol} 1st check passed area: {curr_area} limit: {limit_area}')

        bull_limit_mtrend = float(COSMO_SYMBOLS_PARAMETERS[symbol]['bull_mtrend'])
        bear_limit_mtrend = float(COSMO_SYMBOLS_PARAMETERS[symbol]['bear_mtrend'])

        # 2nd check: mtrend limit reached BUY or SELL
        utils.logger.info(f'{symbol} mtrend: {mtrend} limits: {bear_limit_mtrend} {bull_limit_mtrend}')

        # BUY
        if mtrend < bear_limit_mtrend:
            trade = 'BUY'
        # SELL
        elif mtrend > bull_limit_mtrend:
            trade = 'SELL'
        # NONE
        else:
            trade = None

        if trade:
            utils.logger.info(f'{symbol} 2nd check passed {trade} mtrend: {mtrend}')

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
def helper_find_price_by_peak(symbol_df, peaks):
    """ Find the price given a peak """

    result = []
    for peak in peaks:
        pclose = symbol_df[symbol_df['mtrend'] == peak]['pclose'].iloc[-1]
        result.append(pclose)

    return result

@utils.logger.catch
def get_tp_sl(pclose, pclose_max, pclose_min):
    """ Analyze take profits for short term and long term """

    result = False
    resistance, support = 0.0, 0.0

    resistance = max(pclose_max)
    support = min(pclose_min)

    result_res = True and pclose + (pclose * float(COSMOBOT_CONFIG['tp_rate'])) \
                        <= resistance
    result_sup = True and pclose - (pclose * float(COSMOBOT_CONFIG['sl_rate'])) \
                        >= support

    result = result_res and result_sup

    return result, resistance, support


@utils.logger.catch
def update_cosmo_parameters(symbol):
    """ Update dynamo table with current bot data """
    # pylint: disable=global-variable-not-assigned

    global COSMO_SYMBOLS_PARAMETERS
    utils.logger.info(f' {symbol} Update cosmo parameters')


    symbol_parameter_item = dynamodb.get_item(  AWS_DYNAMO_SESSION,
                                                CONFIG_TABLE_NAME,
                                                {'feature' : f'{symbol}_parameters'})
    symbol_df = COSMO_SYMBOLS_DFS[symbol]
    COSMO_SYMBOLS_PARAMETERS[symbol] = symbol_parameter_item

    # order n
    order_n = int(symbol_parameter_item['order_mtrend'])

    mtrend_array = symbol_df['mtrend'].to_numpy()
    # Find local peaks
    if len(symbol_df) > cosmomixins.MIN_DF_LEN:
        mtrend_maxima = find_peaks(mtrend_array, order=order_n, peak_type='max')
        mtrend_minima = find_peaks(mtrend_array, order=order_n, peak_type='min')

        pclose_maxima = helper_find_price_by_peak(symbol_df, mtrend_maxima)
        pclose_minima = helper_find_price_by_peak(symbol_df, mtrend_minima)

    else:
        utils.logger.info(f'{symbol} Not enough data')
        mtrend_maxima = []
        mtrend_minima = []
        pclose_maxima = []
        pclose_minima = []

    # Update Timestamp
    symbol_parameter_item['timestamp'] = Decimal(utils.get_timestamp(multiplier=1))

    if (len(mtrend_maxima) > 0 ) and (len(mtrend_minima) > 0):

        utils.logger.info(f'{symbol} MAX mtrend peaks {mtrend_maxima}')
        utils.logger.info(f'{symbol} MIN mtrend peaks {mtrend_minima}')

        utils.logger.info(f'{symbol} MAX pclose peaks {pclose_maxima}')
        utils.logger.info(f'{symbol} MIN pclose peaks {pclose_minima}')

        maxima_mean = mtrend_maxima.mean()
        minima_mean = mtrend_minima.mean()

        symbol_parameter_item['bull_mtrend']= Decimal(f'{maxima_mean:.2f}')
        symbol_parameter_item['bear_mtrend'] = Decimal(f'{minima_mean:.2f}')

        # Log parameters
        utils.logger.info(f'{symbol} parameters max: {maxima_mean} min {minima_mean}')

        # Put it on memory
        COSMO_SYMBOLS_PARAMETERS[symbol] = symbol_parameter_item

    else:
        utils.logger.error(f'{symbol} non compliant data')

        symbol_parameter_item['bull_mtrend']= -99
        symbol_parameter_item['bear_mtrend'] = 99

    # Put it on dynamo
    dynamodb.put_item(  AWS_DYNAMO_SESSION,
                        CONFIG_TABLE_NAME,
                        {'feature' : f'{symbol}_parameters',
                        'value' : symbol_parameter_item},
                        'sa-east-1')

    return pclose_maxima, pclose_minima


@utils.logger.catch
def update_cosmo_dfs(symbol, symbol_type):
    """ Update local variables with current data """
    # pylint: disable=global-variable-not-assigned

    global COSMO_SYMBOLS_DFS
    utils.logger.info(f'{symbol} Update cosmo DFs')

    csv_path = f'{CHART_BASE_PATH}{symbol_type}/{symbol}.csv'
    if FROM_LAMBDA:
        symbol_df = cosmomixins.get_resource_optimized_dfs(AWS_DYNAMO_SESSION,
                                                           symbol, csv_path, 5, 521, False, STAGING)
    else:
        symbol_df = cosmomixins.get_resource_optimized_dfs(AWS_DYNAMO_SESSION,
                                                           symbol, csv_path, 5, 521, True, STAGING)

    symbol_df = cosmomixins.aux_format_plotter_df(symbol, symbol_df, 31)

    COSMO_SYMBOLS_DFS[symbol] = symbol_df


@utils.logger.catch
def prepare_msg(call, symbol, pclose, resistance, support, role):
    """ Prepare Discord message """
    # pylint: disable=too-many-arguments

    symbol_name = symbol

    # Prepare message
    msg = f'{call} **{symbol}** - {symbol_name}\n'

    # Float Price for crypto currencies 0.XXXXXX
    if SYMBOL_TYPE == 'CRYPTO' and 'USD' not in symbol:
        msg += f'**Price**: ${pclose:,.5f}\n'
    else:
        # Normal Price for USD symbols based
        msg += f'**Price**: ${pclose:,.2f}\n'

    msg += f'**Resistance**: ${resistance:,.2f}\n'
    msg += f'**Support**: ${support:,.2f}\n'
    msg += f'<@&{role}>'

    return msg


@utils.logger.catch
def check_last_calls(symbol, cosmo_call, mtrend, cosmo_time):
    """ Check last calls and compare to the current call to filter it """

    utils.logger.info(f'{symbol} Checking last calls')
    table_name = 'mm_cosmobot_calls'
    week = cosmo_time[0]
    timestamp = utils.date_ago_timestmp(days=3)

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

    last_call = cosmomixins.aux_format_dynamo_df(pd.DataFrame(info), ignore_outliers=True)
    mask = (last_call['symbol'] == symbol) & (last_call['cosmo_call'] == cosmo_call)
    filter_call = last_call[mask]

    if len(filter_call) == 0:
        return True

    lc_mtrend = filter_call['mtrend'].iloc[-1]

    utils.logger.info(f'{symbol} mtrends last call: {lc_mtrend} current: {mtrend}')
    new_mtrend = abs(lc_mtrend) * float(COSMOBOT_CONFIG['mtrend_factor'])
    utils.logger.info(f'New mtrend {new_mtrend}')

    if  abs(mtrend) > new_mtrend:
        return True

    return False


@utils.logger.catch
def update_yf_symbols_table(symbols, symbol_type):
    """ Use Yfinance to get general info about symbol"""

    timestamp = int(utils.get_timestamp(multiplier=1))
    now = utils.date_now(use_tuple=True, tmz='US/Eastern')
    hour = now[3]
    minute = now[4]

    remove_keys = ['longBusinessSummary', 'companyOfficers', 'uuid']

    # Update info between 600-630 AM
    if hour == 6 and minute <= 30:

        utils.logger.info(f'{symbol_type} Update symbol info')
        for symbol in symbols:
            tik = yf.Ticker(symbol)
            info = tik.info

            # Remove inncessary keys
            for key in remove_keys:
                if key in info.keys():
                    info.pop(key, None)

            # Add primary and sort key
            info['symbol'] = symbol
            info['symbol_type'] = symbol_type
            info['timestamp'] = timestamp

            dynamodb.put_item_from_dict(AWS_DYNAMO_SESSION, info, 'mm_symbols', STAGING)


@utils.logger.catch
def run(symbol, symbol_type):
    """ Routine loop to send message in case of signal """
    # pylint: disable=consider-using-f-string, global-statement, global-variable-not-assigned
    # pylint: disable=too-many-locals, line-too-long

    global COSMOBOT_CONFIG

    # Update Stuff
    update_cosmo_dfs(symbol, symbol_type)
    pclose_max, pclose_min = update_cosmo_parameters(symbol)

    # check for a trading call
    symbol_cosmo_info = COSMO_SYMBOLS_DFS[symbol].iloc[-1]
    mtrend = symbol_cosmo_info['mtrend']

    cosmo_call = check_cosmo_call(symbol, mtrend)

    if cosmo_call:
        # Get Cosmo Time Variables
        cosmo_time = cosmomixins.get_cosmobot_time()

        if check_last_calls(symbol, cosmo_call, mtrend, cosmo_time):
            utils.logger.info(f'{symbol} 3rd check passed: Last call')

            # Get Cosmo Variables
            pclose = symbol_cosmo_info['pclose']
            ptrend = symbol_cosmo_info['ptrend']
            strend = symbol_cosmo_info['strend']
            pd_limit = symbol_cosmo_info['pd_limit']
            pz_limit = symbol_cosmo_info['pz_limit']
            area = symbol_cosmo_info['area']
            area = float('{:.2e}'.format(area))

            # Get Take Profit & Stop Loss
            result, resistance, support = get_tp_sl(pclose, pclose_max, pclose_min)

            if result:
                utils.logger.info(f'{symbol} 4th check passed pclose: {pclose} tp: {resistance} sl: {support}')

                # Prepare message
                msg = prepare_msg(cosmo_call, symbol, pclose, \
                                    resistance, support, DISCORD_COSMOBOT_ROLE)

                if STAGING:
                    utils.logger.info(msg)

                utils.logger.info(f"{cosmo_call} {symbol} sending MSG")
                utils.discord_webhook_send(DISCORD_COSMOBOT_HOOK_URL, 'CosmoBOT', msg)

                utils.logger.info(f"{symbol} saving cosmo call in DB")

                to_put = {  'week'          : cosmo_time[0],
                            'timestamp'     : cosmo_time[4],
                            'cosmo_call'    : cosmo_call,
                            'symbol'        : symbol,
                            'mtrend'        : mtrend,
                            'area'          : area,
                            'strend'        : strend,
                            'ptrend'        : ptrend,
                            'pclose'        : pclose,
                            'resistance'   : resistance,
                            'support'     : support,
                            'pz_limit' : pz_limit,
                            'pd_limit' : pd_limit }

                dynamodb.put_item_from_dict(AWS_DYNAMO_SESSION, to_put, 'mm_cosmobot_calls', STAGING)


@utils.logger.catch
def launch(event=None, context=None, threads_chunks=None, user_symbols=None):
    """ Launch function """
    # pylint: disable=unused-argument, global-statement, too-many-branches

    global COSMOBOT_CONFIG, DISCORD_COSMOBOT_HOOK_URL, US_MARKET_STATUS

    # Load config
    COSMOBOT_CONFIG = dynamodb.load_feature_value_config(   AWS_DYNAMO_SESSION,
                                                            CONFIG_TABLE_NAME)

    # Log path
    if not FROM_LAMBDA and event == 'set_log_path':
        utils.logger_path(COSMOBOT_CONFIG['log_path'])

    if event == 'first_launch':
        utils.logger.info('First launch: only loads config')
        return

    # Get Market Status
    US_MARKET_STATUS = broker.us_market_status()

    symbols = COSMOBOT_CONFIG[f'{SYMBOL_TYPE.lower()}_symbols']
    DISCORD_COSMOBOT_HOOK_URL = os.getenv(f'TF_VAR_COSMOBOT_DISCORD_{SYMBOL_TYPE}_HOOK_URL')

    if SYMBOL_TYPE != 'CRYPTO' and not US_MARKET_STATUS:
        utils.logger.info('US Market close')
        update_yf_symbols_table(symbols, SYMBOL_TYPE)
        symbols = []

    # only run for user input symbols
    symbols = user_symbols if user_symbols else symbols

    # Start bot run() with threads
    if threads_chunks:
        symbols_chunks = utils.divide_list_chunks(symbols, threads_chunks)
        for chunk in symbols_chunks:
            threads = []

            for symbol in chunk:
                runner = threading.Thread(target=run, args=(symbol, SYMBOL_TYPE))
                threads.append(runner)
                runner.start()

            for thread in threads:
                thread.join()
    # No threading
    else:
        for symbol in symbols:
            run(symbol, SYMBOL_TYPE)
