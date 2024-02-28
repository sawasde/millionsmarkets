""" Cosmo BOT module to send signals calls"""
# pylint: disable=no-name-in-module, import-error, R0801

import os
import threading
import yfinance as yf
import numpy as np
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
CONFIG_TABLE_NAME = 'mm_cosmobot'

# cosmobot vars
COSMOBOT_CONFIG = {}
CHART_BASE_PATH = 'assets/'
COSMO_SYMBOLS_PARAMETERS = {}
COSMO_SYMBOLS_DFS = {}
SYMBOL_TYPE = os.getenv('TF_VAR_SYMBOL_TYPE')
US_MARKET_STATUS = True

@utils.logger.catch
def check_cosmo_call(symbol, mtrends, curr_area):
    """ Rules to call for a signal """
    # pylint: disable=global-variable-not-assigned, line-too-long

    if len(COSMO_SYMBOLS_DFS[symbol]) < cosmomixins.MIN_DF_LEN:
        return None

    limit_area = float(COSMO_SYMBOLS_PARAMETERS[symbol]['limit_area'])
    trade = None

    # 1st check: LongTerm trend
    if abs(curr_area) > limit_area:
        utils.logger.info(f'{symbol} 1st check passed area: {curr_area} limit: {limit_area}')

        bull_limit_mtrend = float(COSMO_SYMBOLS_PARAMETERS[symbol]['bull_mtrend'])
        bear_limit_mtrend = float(COSMO_SYMBOLS_PARAMETERS[symbol]['bear_mtrend'])

        for mtrend in mtrends:

            # BUY
            if mtrend < bear_limit_mtrend:
                trade = 'BUY'

            # SELL
            elif mtrend > bull_limit_mtrend:
                trade = 'SELL'

            if trade:
                # 2nd check: mtrend limit reached BUY or SELL
                utils.logger.info(f'{symbol} mtrend: {mtrend} limits: {bear_limit_mtrend} {bull_limit_mtrend}')
                utils.logger.info(f'{symbol} 2nd check passed {trade} mtrend: {mtrend}')
                break

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


    symbol_parameter_item = dynamodb.load_feature_value_config( AWS_DYNAMO_SESSION,
                                                                CONFIG_TABLE_NAME,
                                                                f'{symbol}_parameters',
                                                                STAGING)
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
    symbol_parameter_item['timestamp'] = utils.get_timestamp(multiplier=1)

    if (len(mtrend_maxima) > 0 ) and (len(mtrend_minima) > 0):

        utils.logger.info(f'{symbol} MAX mtrend peaks {mtrend_maxima}')
        utils.logger.info(f'{symbol} MIN mtrend peaks {mtrend_minima}')

        utils.logger.info(f'{symbol} MAX pclose peaks {pclose_maxima}')
        utils.logger.info(f'{symbol} MIN pclose peaks {pclose_minima}')

        maxima_mean = mtrend_maxima.mean()
        minima_mean = mtrend_minima.mean()

        symbol_parameter_item['bull_mtrend']= float(f'{maxima_mean:.2f}')
        symbol_parameter_item['bear_mtrend'] = float(f'{minima_mean:.2f}')

        # Log parameters
        utils.logger.info(f'{symbol} parameters max: {maxima_mean} min {minima_mean}')

        # Put it on memory
        COSMO_SYMBOLS_PARAMETERS[symbol] = symbol_parameter_item

    else:
        utils.logger.error(f'{symbol} non compliant data')

        symbol_parameter_item['bull_mtrend']= -99
        symbol_parameter_item['bear_mtrend'] = 99

    # Put it on dynamo
    to_put = {'feature' : f'{symbol}_parameters', 'value' : symbol_parameter_item}
    to_put['value']['order_mtrend'] = order_n

    dynamodb.put_item_from_dict(AWS_DYNAMO_SESSION, CONFIG_TABLE_NAME, to_put, STAGING)

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
def prepare_msg(call, symbol, pclose, resistance, support, mtrend):
    """ Prepare message """
    # pylint: disable=too-many-arguments

    stock_country_codes = ['.CL', '.DE', '.WA']
    # get symbol YF info
    symbol_info = helper_get_symbol_data(symbol)

    # Prepare message
    for stock_code in stock_country_codes:
        if stock_code in symbol:
            symbol_print = symbol.replace(stock_code, '')
        else:
            symbol_print = symbol

    msg = f'{call} **{symbol_print}** - {symbol_info["longName"]}\n'

    # Float Price for crypto currencies 0.XXXXXX
    if SYMBOL_TYPE == 'CRYPTO' and 'USD' not in symbol:
        msg += f'**Price**: ${pclose:,.5f}\n'
    else:
        # Normal Price for USD symbols based
        msg += f'**Price**: ${pclose:,.2f}\n'

    msg += f'**Resistance**: ${resistance:,.2f}\n'
    msg += f'**Support**: ${support:,.2f}\n'
    msg += f'**Mtrend**: ${mtrend:,.2f}\n'

    for key, value in symbol_info.items():
        if key == 'longName':
            continue
        if value:
            msg += f'**{key.capitalize()}**: {value}\n'

    return msg


@utils.logger.catch
def helper_get_symbol_data(symbol):
    """ Get the main data given a symbol """

    table_name = 'mm_symbols'
    symbol_info = {'country':'', 'industry':'', 'sector':'', 'longName':''}

    if STAGING:
        table_name += '_staging'

    info = dynamodb.query_items(dyn_session=AWS_DYNAMO_SESSION,
                                table_name=table_name,
                                pkey='symbol',
                                pvalue=symbol,
                                query_type='partition')
    info = info[-1]

    for key_data in symbol_info:
        if key_data in info.keys():
            symbol_info[key_data] = info[key_data]

    return symbol_info


@utils.logger.catch
def check_last_calls(symbol, cosmo_call, pclose):
    """ Check last calls and compare to the current call to filter it """
    # pylint: disable=superfluous-parens

    utils.logger.info(f'{symbol} {cosmo_call} Checking last calls')
    table_name = 'mm_cosmobot_calls'

    # Take 1 year of info
    weeks_ago = int(COSMOBOT_CONFIG['weeks_ago_last_call'])

    # profit factor
    profit_factor = float(COSMOBOT_CONFIG['profit_factor'])

    # Get last calls DF
    last_calls_df = cosmomixins.cosmobot_historical_to_df(AWS_DYNAMO_SESSION,
                                                          table_name,
                                                          weeks_ago,
                                                          None,
                                                          True,
                                                          STAGING)

    # Filter by symbol
    symbol_call_df = last_calls_df[last_calls_df['symbol'] == symbol]
    symbol_call_list = symbol_call_df['cosmo_call'].to_list()

    # Prioritize BUY filtering
    if 'BUY' in symbol_call_list:
        buy_mask = (symbol_call_df['cosmo_call'] == 'BUY')
        last_buy_pclose = symbol_call_df[buy_mask]['pclose'].iloc[-1]

    # Call BUY
    if cosmo_call == 'BUY':
        # Frequent case empty symbol DF
        if  (len(symbol_call_df) == 0) or \
            ('BUY' not in symbol_call_list) or \
            (pclose <= ((last_buy_pclose*(3 - profit_factor)/2))):

            utils.logger.info(f'{symbol} {cosmo_call} call in {weeks_ago} weeks')
            return True

    # Call SELL
    if cosmo_call == 'SELL':
        if (len(symbol_call_df) == 0) or \
            ('BUY' not in symbol_call_list):

            utils.logger.info(f'{symbol} {cosmo_call} First call in {weeks_ago} weeks')
            return False

        if pclose >= last_buy_pclose*profit_factor:
            utils.logger.info(f'{symbol} {cosmo_call} profit factor {profit_factor} reached')

            if 'SELL' in symbol_call_list:

                timestamp = utils.date_ago_timestmp(days=8)

                # Pick SELL calls with a timestamp ago. old SELL signals are discarded
                sell_mask = (symbol_call_df['cosmo_call'] == 'SELL') & \
                            (symbol_call_df['timestamp'] >= timestamp)

                last_sell_pclose_df = symbol_call_df[sell_mask]

                if len(last_sell_pclose_df) == 0:
                    return True

                last_sell_pclose = last_sell_pclose_df['pclose'].iloc[-1]

                if pclose < last_sell_pclose*profit_factor:
                    return False

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

            dynamodb.put_item_from_dict(AWS_DYNAMO_SESSION, 'mm_symbols', info, STAGING)


@utils.logger.catch
def run(symbol, symbol_type):
    """ Routine loop to send message in case of signal """
    # pylint: disable=consider-using-f-string, global-statement, global-variable-not-assigned
    # pylint: disable=too-many-locals, line-too-long

    global COSMOBOT_CONFIG

    # Update Stuff
    update_cosmo_dfs(symbol, symbol_type)
    pclose_max, pclose_min = update_cosmo_parameters(symbol)

    # Get last symbol data
    symbol_cosmo_info = COSMO_SYMBOLS_DFS[symbol].iloc[-1]

    # Get last mtrends
    last_mtrends = int(COSMOBOT_CONFIG['last_mtrends_to_check'])

    if SYMBOL_TYPE == 'CRYPTO':
        last_mtrends *= 3

    mtrends = COSMO_SYMBOLS_DFS[symbol]['mtrend'].iloc[-last_mtrends:].to_list()
    area = symbol_cosmo_info['area']
    area = float('{:.2e}'.format(area))

    # Check for cosmo_call
    cosmo_call = check_cosmo_call(symbol, mtrends, area)

    if cosmo_call:
        # Get Cosmo Time Variables
        cosmo_time = cosmomixins.get_cosmobot_time()

        # Get the pclose
        pclose = symbol_cosmo_info['pclose']

        if check_last_calls(symbol, cosmo_call, pclose):

            utils.logger.info(f'{symbol} 3rd check passed: Last call')

            # Get Cosmo Variables
            ptrend = symbol_cosmo_info['ptrend']
            strend = symbol_cosmo_info['strend']
            mtrend = symbol_cosmo_info['mtrend']
            pd_limit = symbol_cosmo_info['pd_limit']
            pz_limit = symbol_cosmo_info['pz_limit']

            # Get Take Profit & Stop Loss
            result, resistance, support = get_tp_sl(pclose, pclose_max, pclose_min)

            if result:
                utils.logger.info(f'{symbol} 4th check passed pclose: {pclose} tp: {resistance} sl: {support}')

                # Prepare message
                msg = prepare_msg(cosmo_call, symbol, pclose, \
                                    resistance, support, mtrend)

                if STAGING:
                    utils.logger.info(msg)

                utils.logger.info(f"{cosmo_call} {symbol} sending MSG")
                #TO-DO Send to telegram
                #
                #

                # Send to discord
                msg += f'<@&{DISCORD_COSMOBOT_ROLE}>'
                utils.discord_webhook_send(DISCORD_COSMOBOT_HOOK_URL, 'CosmoBOT', msg)

                # Save signal in DB
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

                dynamodb.put_item_from_dict(AWS_DYNAMO_SESSION, 'mm_cosmobot_calls', to_put, STAGING)


@utils.logger.catch
def launch(event=None, context=None, threads_chunks=None, user_symbols=None):
    """ Launch function """
    # pylint: disable=unused-argument, global-statement, too-many-branches

    global COSMOBOT_CONFIG, DISCORD_COSMOBOT_HOOK_URL, US_MARKET_STATUS

    # Load config
    COSMOBOT_CONFIG = dynamodb.load_feature_value_config(   AWS_DYNAMO_SESSION,
                                                            CONFIG_TABLE_NAME,
                                                            'config',
                                                            STAGING)

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
