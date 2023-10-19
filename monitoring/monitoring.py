""" Utils module containing helper functions """
# pylint: disable=no-name-in-module

import os
import threading
from utils import utils, dynamodb

#Staging
STAGING = bool(int(os.getenv('TF_VAR_STAGING')))
FROM_LAMBDA = bool(int(os.getenv('TF_VAR_FROM_LAMBDA')))

# Discord vars
DISCORD_MONITORING_HOOK_URL = os.getenv('TF_VAR_MONITORING_DISCORD_HOOK_URL')
DISCORD_MONITORING_ROLE = os.getenv('TF_VAR_MONITORING_DISCORD_ROLE')

# AWS Dynamo
AWS_DYNAMO_SESSION = dynamodb.create_session(from_lambda=FROM_LAMBDA)
CONFIG_TABLE_NAME = None

# Monitoring VARS
CA_SYMBOLS_TIMESTAMPS = {}
MONITORING_RESULTS = {  'cosmoagent' : {'cryptos': {}, 'stocks': {}},
                        'cosmobot' : {'cryptos': {}, 'stocks': {}}}
SYMBOLS_BASE_PATH = 'monitoring/assets/'
CSV_ASSET_PATH = '{}{}.csv'


@utils.logger.catch
def monitor_cosmoagent(symbol_set, symbol):
    """ Search for a cosmoagent historical symbol and compare the timestamp
        Use X minutes diff"""

    # In case stock market is off, return True
    if symbol_set == 'stocks' and not utils.is_stock_market_hours():
        return True

    if symbol not in CA_SYMBOLS_TIMESTAMPS.keys():
        return False

    now_tms = CA_SYMBOLS_TIMESTAMPS[symbol]
    diff_tms = utils.date_ago_timestmp(minutes=10)

    if now_tms > diff_tms:
        return True

    return False


@utils.logger.catch
def monitor_cosmobot(symbol_set, symbol):
    """ Search for a cosmobot symbol parameters and compare the timestamp
        Use X minutes diff"""

    # In case stock market is off, return True
    if symbol_set == 'stocks' and not utils.is_stock_market_hours():
        return True

    symbol_parameter_item = dynamodb.load_feature_value_config(  AWS_DYNAMO_SESSION,
                                                                CONFIG_TABLE_NAME,
                                                                f'{symbol}_parameters')

    now_tms = symbol_parameter_item['timestamp']
    diff_tms = utils.date_ago_timestmp(minutes=20)

    if now_tms > diff_tms:
        return True

    return False


@utils.logger.catch
def send_monitoring_report(bot):
    """ Send via Discord the monitoring report """

    general_status = True
    msg = f'**{bot.upper()}  Status:**\n'
    send_alert= False

    for symbol_set, symbol_info in MONITORING_RESULTS[bot].items():
        msg += f'**{symbol_set.upper()}:\n**'

        for symbol, status in symbol_info.items():

            general_status = False if not status else general_status
            msg += f'{symbol}: '
            msg += ':white_check_mark:' if status else ':x:'
            msg += '\t'
        msg += '\n'

    msg += '\n'

    # Report all symbols each 6 hours
    curr_hour = utils.date_now()[3]
    if curr_hour % 6 == 0:
        send_alert = True

    # If general status is FAIL then sned message
    # AND Alert @Role that something failed
    if not general_status:
        msg += f'<@&{DISCORD_MONITORING_ROLE}>'
        send_alert = True

    if send_alert:
        utils.logger.info(f'{bot} Sending Alert')
        utils.discord_webhook_send(DISCORD_MONITORING_HOOK_URL, 'MonitoringBOT', msg)


@utils.logger.catch
def run(bot, symbol_set, symbol):
    """ Run Monitoring for each bot"""
    # pylint: disable=global-variable-not-assigned

    global MONITORING_RESULTS

    function_name = f'monitor_{bot}'
    func =  globals()[function_name]

    MONITORING_RESULTS[bot][symbol_set][symbol] = func(symbol_set, symbol)


def launch(event=None, context=None):
    """ Load configs and run once the agent """
    # pylint: disable=unused-argument, global-statement

    global CONFIG_TABLE_NAME, CA_SYMBOLS_TIMESTAMPS
    bots = MONITORING_RESULTS.keys()

    try:

        for monitoring_bot in bots:

            if STAGING:
                CONFIG_TABLE_NAME = f'mm_{monitoring_bot}_staging'
            else:
                CONFIG_TABLE_NAME = f'mm_{monitoring_bot}'

            if monitoring_bot == 'cosmoagent':
                CA_SYMBOLS_TIMESTAMPS = dynamodb.load_feature_value_config( AWS_DYNAMO_SESSION,
                                                            CONFIG_TABLE_NAME,
                                                            'symbols_timestamps')
            # Load config
            bot_config = dynamodb.load_feature_value_config(   AWS_DYNAMO_SESSION,
                                                                CONFIG_TABLE_NAME)

            symbols_set = {'cryptos': bot_config['crypto_symbols'],
                        'stocks':bot_config['stock_symbols']}

            # Start bot run() with threads
            threads = []

            for sym_set, symbols in symbols_set.items():
                for symbol in symbols:

                    runner = threading.Thread(target=run, args=(monitoring_bot, sym_set, symbol,))
                    threads.append(runner)
                    runner.start()

                for thread in threads:
                    thread.join()

            if len(MONITORING_RESULTS[monitoring_bot]) > 0:
                send_monitoring_report(monitoring_bot)

    except Exception as e:
        msg = f'**BOT error**: {e}\n'
        msg += f'<@&{DISCORD_MONITORING_ROLE}>'

        utils.discord_webhook_send(DISCORD_MONITORING_HOOK_URL, 'MonitoringBOT', msg)
