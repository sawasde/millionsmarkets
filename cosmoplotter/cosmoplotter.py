""" Plotter Function """
# pylint: disable=no-name-in-module, import-error

import os
import time
import threading
# local imports
from utils import utils, dynamodb, cosmomixins, plotting


# General vars
COSMOBOT_CONFIG = {}
CHART_BASE_PATH = 'cosmoplotter/assets/'
TMS_TRESSHOLD_SEC = 260

# AWS Dynamo
STAGING = bool(int(os.getenv('TF_VAR_STAGING')))
AWS_DYNAMO_SESSION = dynamodb.create_session()

if STAGING:
    TABLE_NAME = 'mm_cosmobot_staging'
else:
    TABLE_NAME = 'mm_cosmobot'



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

    utils.logger.info(symbol, day, 'PLOT SAVED')


@utils.logger.catch
def remove_plot(symbol):
    """ Remove all local pictures """
    # pylint: disable=unused-variable
    #filename = search_for_file_extension(symbol, )
    for root, dirs, files in os.walk(CHART_BASE_PATH):
        for basename in files:
            filename = os.path.join(root, basename)

            if symbol in filename and (filename.endswith('.png')
                                       or filename.endswith('.html')):
                os.remove(filename)


@utils.logger.catch
def run(symbol, days_ago, symbol_type):
    """ Main function """

    # Remove previous plots
    utils.logger.info(f'{symbol} Removing plots ...')
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
    for root, dirs, files in os.walk(CHART_BASE_PATH):
            for basename in files:
                filename = os.path.join(root, basename)

                if symbol in filename and filename.endswith(ext):
                    return filename

@utils.logger.catch
def create_main_html(symbols, symbol_type):

    html_output_file = f'{CHART_BASE_PATH}{symbol_type}/main.html'
    for symbol in symbols:
        filename = search_for_file_extension(symbol, '.html')

        if filename:
            with open(html_output_file, 'a') as f:
                f.write(f'<h1>{symbol} CHART:</h1>\n')
                with open(filename, 'r') as symbol_html:
                    f.write(symbol_html)



@utils.logger.catch
def launch(symbol_type='stock'):
    """ Launch fucntion """
    # pylint: disable=global-statement
    global COSMOBOT_CONFIG

    # Load config
    COSMOBOT_CONFIG = dynamodb.load_feature_value_config(AWS_DYNAMO_SESSION, TABLE_NAME)

    #Start bot run() with threads
    threads = []
    if symbol_type == 'crypto':
        symbols = COSMOBOT_CONFIG['crypto_symbols']
    elif symbol_type == 'stock':
        symbols = COSMOBOT_CONFIG['stock_symbols']
    elif symbol_type == 'both':
        symbols = COSMOBOT_CONFIG['crypto_symbols'] + COSMOBOT_CONFIG['stock_symbols']
    else:
        symbols = []

    for symbol in symbols:

        runner = threading.Thread(target=run, args=(symbol,[31],symbol_type,))
        threads.append(runner)
        runner.start()
        time.sleep(0.3)

    for thread in threads:
        thread.join()

    create_main_html(symbols, symbol_type)
