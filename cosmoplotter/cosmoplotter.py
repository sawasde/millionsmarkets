""" Plotter Function """
# pylint: disable=no-name-in-module, import-error

import os
import threading
# local imports
from utils import utils, dynamodb, cosmomixins, plotting


# General vars
COSMOBOT_CONFIG = {}
CHART_BASE_PATH = 'cosmoplotter/assets/'
CSV_ASSET_PATH = '{}{}.csv'
TMS_TRESSHOLD_SEC = 260

# AWS Dynamo
STAGING = bool(int(os.getenv('TF_VAR_STAGING')))
AWS_DYNAMO_SESSION = dynamodb.create_session()

if STAGING:
    TABLE_NAME = 'mm_cosmobot_staging'
else:
    TABLE_NAME = 'mm_cosmobot'



@utils.logger.catch
def plotter(symbol, df_initial, day):
    """ Main Function to plot symbol cosmo data """

    df_result = cosmomixins.aux_format_plotter_df(symbol, df_initial, day)

    png_file_path_temp = f'{CHART_BASE_PATH}{symbol}_{day}.png'

    plotting.plot_sublots(  df_initial=df_result,
                            plot_features_dicts=[{'pclose':'g', 'pz_limit':'b'},
                                                {'area':'r', 'zero_bound':'b'},
                                                {'mtrend':'g', 'zero_bound':'b'},
                                                ],
                        xaxis='timestamp', save=png_file_path_temp, style='-', show=False)
    utils.logger.info(symbol, day, 'PLOT SAVED')


@utils.logger.catch
def remove_plot(symbol):
    """ Remove all local pictures """
    # pylint: disable=unused-variable

    for root, dirs, files in os.walk(CHART_BASE_PATH):
        for basename in files:
            filename = os.path.join(root, basename)

            if symbol in filename and filename.endswith('.png'):
                os.remove(filename)


@utils.logger.catch
def run(symbol, days_ago):
    """ Main function """

    # Remove previous plots
    utils.logger.info(f'{symbol} Removing plots ...')
    remove_plot(symbol)

    for day in days_ago:
        # Get df
        weeks = 1 + (day // 7)
        utils.logger.info(f'{symbol} days: {day} weeks: {weeks}')
        print('WEEKS: ',weeks)
        # Check DFs
        utils.logger.info(f'{symbol} Checking DFs')
        csv_path = CSV_ASSET_PATH.format(CHART_BASE_PATH, symbol)
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
        plotter(symbol, df_result, day)


@utils.logger.catch
def launch(symbol_type='both'):
    """ Launch fucntion """
    # pylint: disable=global-statement
    global COSMOBOT_CONFIG

    # Load config
    COSMOBOT_CONFIG = dynamodb.load_feature_value_config(AWS_DYNAMO_SESSION, TABLE_NAME)

    # Log config
    utils.logger.info(COSMOBOT_CONFIG)

    # Start bot run() with threads
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
        runner = threading.Thread(target=run, args=(symbol,[31, 13],))
        threads.append(runner)
        runner.start()

    for thread in threads:
        thread.join()
