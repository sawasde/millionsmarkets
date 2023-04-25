import os
import pandas as pd
# local imports
from utils import utils, dynamodb, cosmomixins, plotting

# AWS Dynamo
AWS_DYNAMO_SESSION = dynamodb.create_session()

# General vars
COSMOBOT_CONFIG = {}
CHART_BASE_PATH = 'cosmoplotter/assets/'
CSV_ASSET_PATH = '{}{}.csv'
TMS_TRESSHOLD_SEC = 260



@utils.logger.catch
def plotter(symbol, df, day):

    df_result = cosmomixins.aux_format_plotter_df(df, day)

    png_file_path_temp = f'{CHART_BASE_PATH}{symbol}_{day}.png'

    plotting.plot_sublots( df=df_result, 
                        plot_features_dicts=[{'pclose':'g', 'pz_limit':'b'},
                                            {'area':'r', 'zero_bound':'b'},
                                            {'mtrend':'g', 'zero_bound':'b'},
                                            ],
                        xaxis='timestamp', save_picture=png_file_path_temp, style='-', show=False)
    utils.logger.info(symbol, day, 'PLOT SAVED')


@utils.logger.catch
def remove_all_plots():

    for root, dirs, files in os.walk(CHART_BASE_PATH):
        for basename in files:
            filename = os.path.join(root, basename)
            
            if filename.endswith(f'.png'):
                os.remove(filename)


@utils.logger.catch
def main(unit_test=False, days_ago=[31,13]):
    ''' Main method '''

    # Remove previous plots
    utils.logger.info('Removing plots ...')
    remove_all_plots()

    for symbol in COSMOBOT_CONFIG['crypto_symbols']:

        for day in days_ago:
            # Get df
            weeks = 1 + (day // 7)
            utils.logger.info(f'Get info for {symbol} days: {day} weeks: {weeks}')

            # Check DFs
            utils.logger.info('Checking DFs')
            csv_path = CSV_ASSET_PATH.format(CHART_BASE_PATH, symbol)
            df = cosmomixins.get_resource_optimized_dfs(AWS_DYNAMO_SESSION, symbol, csv_path, weeks, 521)

            # Plot
            utils.logger.info('Plotting ...')
            plotter(symbol, df, day)


@utils.logger.catch
def launch():
    global COSMOBOT_CONFIG
    
    # Load config
    COSMOBOT_CONFIG = dynamodb.load_feature_value_config(AWS_DYNAMO_SESSION, 'mm_cosmobot')

    # Log config
    utils.logger.info(COSMOBOT_CONFIG)

    main()
    