""" Plotter Function """
# pylint: disable=no-name-in-module, import-error

import os
import time
import threading
# local imports
from utils import utils, dynamodb, cosmomixins, plotting, broker


# AWS Dynamo
STAGING = bool(int(os.getenv('TF_VAR_STAGING')))
AWS_DYNAMO_SESSION = dynamodb.create_session()

if STAGING:
    TABLE_NAME = 'mm_cosmobot_staging'
else:
    TABLE_NAME = 'mm_cosmobot'

# Cosmoplotter vars
COSMOBOT_CONFIG = {}
CHART_BASE_PATH = 'assets/'
TMS_TRESSHOLD_SEC = 260
SYMBOL_TYPE = os.getenv('TF_VAR_SYMBOL_TYPE')
US_MARKET_STATUS = True

@utils.logger.catch
def plotter(symbol, df_initial, day, symbol_type):
    """ Main Function to plot symbol cosmo data """

    df_result = cosmomixins.aux_format_plotter_df(symbol, df_initial, day)

    png_file_path_temp = f'{CHART_BASE_PATH}/{symbol_type}/{symbol}_{day}.png'
    html_file_path_temp = f'{CHART_BASE_PATH}/{symbol_type}/{symbol}_{day}.html'

    plotting.plot_sublots(  df_initial=df_result,
                            plot_features_dicts=[{'pclose':'g', 'pz_limit':'b'},
                                                {'area':'r', 'zero_bound':'b'},
                                                {'mtrend':'g', 'zero_bound':'b'},
                                                ],
                            xaxis='timestamp',
                            save=png_file_path_temp,
                            html=html_file_path_temp,
                            style='-',
                            show=False)

    utils.logger.info(f'{symbol}_{day} PLOT SAVED')


@utils.logger.catch
def remove_plot(symbol):
    """ Remove all local pictures """

    utils.logger.info(f'{symbol} Removing plots ...')
    delete_exts = ['.png', '.html']

    for ext in delete_exts:
        filename = search_for_file_extension(symbol, ext)
        if filename:
            os.remove(filename)


@utils.logger.catch
def run(symbol, days_ago, symbol_type):
    """ Main function """

    # Remove previous plots
    remove_plot(symbol)

    for day in days_ago:
        # Get df
        weeks = 1 + (day // 7)
        utils.logger.info(f'{symbol} days: {day} weeks: {weeks}')

        # Check DFs
        utils.logger.info(f'{symbol} Checking DFs')
        csv_path = f'{CHART_BASE_PATH}{symbol_type}/{symbol}.csv'

        df_result = cosmomixins.get_resource_optimized_dfs( AWS_DYNAMO_SESSION,
                                                            symbol,
                                                            csv_path,
                                                            weeks,
                                                            521,
                                                            True,
                                                            STAGING,
                                                            True)

        # Plot
        utils.logger.info(f'{symbol} Plotting ...')
        plotter(symbol, df_result, day, symbol_type)

@utils.logger.catch
def search_for_file_extension(symbol, ext):
    """ search a file containing the symbol and extension """
    # pylint: disable=unused-variable

    for root, dirs, files in os.walk(CHART_BASE_PATH):
        for basename in files:
            filename = os.path.join(root, basename)

            if symbol in filename and filename.endswith(ext):
                return filename
    return None

@utils.logger.catch
def create_main_html(symbols, symbol_type):
    """ Create a main html plotter file """

    utils.logger.info(f'Create main html file for {symbol_type}')
    html_output_file = f'{CHART_BASE_PATH}{symbol_type}/main.html'

    if os.path.isfile(html_output_file):
        os.remove(html_output_file)

    for symbol in symbols:
        filename_html = search_for_file_extension(symbol, '.html')

        if filename_html:
            with open(html_output_file, 'a', encoding='utf-8') as main_html,\
                    open(filename_html, 'r', encoding='utf-8') as part_html:
                main_html.write(f'<h1>{symbol} CHART:</h1>\n')
                main_html.write(part_html.read())



@utils.logger.catch
def launch(user_symbols=None):
    """ Launch fucntion """
    # pylint: disable=global-statement
    global COSMOBOT_CONFIG, US_MARKET_STATUS

    # Load config
    COSMOBOT_CONFIG = dynamodb.load_feature_value_config(AWS_DYNAMO_SESSION, TABLE_NAME)

    #Start bot run() with threads
    threads = []
    # Get Market Status
    US_MARKET_STATUS = broker.us_market_status()

    if SYMBOL_TYPE == 'CRYPTO':
        symbols = COSMOBOT_CONFIG['crypto_symbols']
    elif SYMBOL_TYPE == 'STOCK' and US_MARKET_STATUS:
        symbols = COSMOBOT_CONFIG['stock_symbols']
    elif SYMBOL_TYPE == 'ETF' and US_MARKET_STATUS:
        symbols = COSMOBOT_CONFIG['etf_symbols']
    else:
        if not US_MARKET_STATUS:
            utils.logger.info('US Market close')
        else:
            utils.logger.error(f'Wrong Symbol Type: {SYMBOL_TYPE}')
        symbols = []

    symbols = user_symbols if user_symbols else symbols

    for symbol in symbols:

        runner = threading.Thread(target=run, args=(symbol,[31], SYMBOL_TYPE,))
        threads.append(runner)
        runner.start()
        time.sleep(0.3)

    for thread in threads:
        thread.join()

    create_main_html(symbols, SYMBOL_TYPE)
