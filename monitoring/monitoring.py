""" Utils module containing helper functions """
# pylint: disable=no-name-in-module

import os
import threading
from utils import utils, dynamodb, cosmomixins

#Staging
STAGING = bool(int(os.getenv('TF_VAR_STAGING')))
FROM_LAMBDA = bool(int(os.getenv('TF_VAR_FROM_LAMBDA')))

# Discord vars
DISCORD_MONITORING_HOOK_URL = os.getenv('TF_VAR_MONITORING_DISCORD_HOOK_URL')

# AWS Dynamo
AWS_DYNAMO_SESSION = dynamodb.create_session(from_lambda=FROM_LAMBDA)
CONFIG_TABLE_NAME = None

# Monitoring VARS
MONITORING_RESULTS = { 'cosmoagent' : {}, 'cosmobot' : {}}
SYMBOLS_BASE_PATH = 'monitoring/assets/'
CSV_ASSET_PATH = '{}{}.csv'


@utils.logger.catch
def monitor_cosmoagent(symbol):
    """ Search for a cosmoagent historical symbol and compare the timestamp
        Use 2 minutes diff"""
    csv_path = CSV_ASSET_PATH.format(SYMBOLS_BASE_PATH, symbol)

    if FROM_LAMBDA:
        symbol_df = cosmomixins.get_resource_optimized_dfs(AWS_DYNAMO_SESSION,
                                                           symbol, csv_path, 1, 99, False, STAGING)
    else:
        symbol_df = cosmomixins.get_resource_optimized_dfs(AWS_DYNAMO_SESSION,
                                                            symbol, csv_path, 1, 99, True, STAGING)

    now_tms = symbol_df['timestamp'].iloc[-1]
    diff_tms = utils.date_ago_timestmp(minutes=4)

    if now_tms > diff_tms:
        return True

    return False


@utils.logger.catch
def monitor_cosmobot(symbol):
    """ Search for a cosmobot symbol parameters and compare the timestamp
        Use 10 minutes diff"""

    symbol_parameter_item = dynamodb.get_item(  AWS_DYNAMO_SESSION,
                                                CONFIG_TABLE_NAME,
                                                {'feature' : f'{symbol}_parameters'})

    now_tms = symbol_parameter_item['timestamp']
    diff_tms = utils.date_ago_timestmp(minutes=10)

    if now_tms > diff_tms:
        return True

    return False


@utils.logger.catch
def send_monitoring_report(bot):
    """ Send via Discord the monitoring report """

    utils.logger.info(f'{bot} Sending Report')

    msg = f'**{bot.upper()} Report:\n**'

    for symbol, status in MONITORING_RESULTS[bot].items():

        msg += f'{symbol}\t'
        msg += ':white_check_mark:' if status else ':x:'
        msg += '\n'

    msg += '-' *15 + '\n'
    utils.discord_webhhok_send(DISCORD_MONITORING_HOOK_URL, 'MonitoringBOT', msg)


@utils.logger.catch
def run(bot, symbol):
    """ Run Monitoring for each bot"""
    # pylint: disable=global-variable-not-assigned

    global MONITORING_RESULTS

    function_name = f'monitor_{bot}'
    func =  globals()[function_name]

    MONITORING_RESULTS[bot][symbol] = func(symbol)


@utils.logger.catch
def launch(event=None, context=None):
    """ Load configs and run once the agent """
    # pylint: disable=unused-argument, global-statement

    global CONFIG_TABLE_NAME

    bots = MONITORING_RESULTS.keys()

    for monitoring_bot in bots:

        if STAGING:
            CONFIG_TABLE_NAME = f'mm_{monitoring_bot}_staging'
        else:
            CONFIG_TABLE_NAME = f'mm_{monitoring_bot}'

        # Load config
        bot_config = dynamodb.load_feature_value_config(   AWS_DYNAMO_SESSION,
                                                            CONFIG_TABLE_NAME)

        # Start bot run() with threads
        threads = []

        for symbol in bot_config['crypto_symbols']:

            runner = threading.Thread(target=run, args=(monitoring_bot, symbol,))
            threads.append(runner)
            runner.start()

        for thread in threads:
            thread.join()

        if len(MONITORING_RESULTS[monitoring_bot]) > 0:
            send_monitoring_report(monitoring_bot)
