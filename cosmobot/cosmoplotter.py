import os
import pandas as pd
# local imports
from utils import utils, dynamodb
from cosmobot import cosmomixins

# AWS Dynamo
AWS_DYNAMO_SESSION = dynamodb.create_session()

# General vars
COSMOAGENT_CONFIG = {}
CHART_BASE_PATH = 'cosmobot/assets/'
CSV_ASSET_PATH = '{}{}.csv'
TMS_TRESSHOLD_SEC = 260



@logger.catch
def plotter(symbol, df, day):

    df['zero_bound'] = 0

    if len(df) < 2:
        return

    day_tms = utils.date_ago_timestmp(xtb_tms=False, days=int(day))
    print(symbol, day, day_tms)

    df_temp = df[df['timestamp'] >= day_tms]

    # AREA STUFF
    df_temp = utils.integrate_area_below(df_temp, yaxis='ptrend', dx=1)

    png_file_path_temp = f'{CHART_BASE_PATH}{symbol}_{day}.png'

    utils.plot_sublots( df=df_temp, 
                        plot_features_dicts=[{'pclose':'g', 'pz_limit':'b', 'pd_limit': 'r'},
                                            {'area':'r', 'zero_bound':'b'},
                                            {'mtrend':'g', 'zero_bound':'b'},
                                            ],
                        xaxis='timestamp', save_picture=png_file_path_temp, style='-', show=False)
    (symbol, day, 'PLOT SAVED')



@logger.catch
def remove_all_plots():

    for root, dirs, files in os.walk(CHART_BASE_PATH):
        for basename in files:
            filename = os.path.join(root, basename)
            
            if filename.endswith(f'.png'):
                os.remove(filename)


@logger.catch
def main(unit_test=False, days_ago=[31,13]):
    ''' Main method '''

    # Remove previous plots
    utils.logger.info('Removing plots ...')
    remove_all_plots()

    for symbol in COSMOAGENT_CONFIG['crypto_symbols']:

        for day in days_ago:
            # Get df
            weeks = 1 + (day // 7)
            utils.logger.info(f'Get info for {symbol} days: {day} weeks: {weeks}')

            # Check DFs
            utils.logger.info('Checking DFs')
            csv_path = CSV_ASSET_PATH.format(CHART_BASE_PATH, symbol)
            df = cosmomixins.get_resource_optimized_dfs(AWS_DYNAMO_SESSION, symbol, csv_path, weeks)
            return

            # Plot
            utils.logger.info('Plotting ...')
            plotter(symbol, df, day)


@logger.catch
def launch():
    global COSMOAGENT_CONFIG
    
    # Load config
    COSMOAGENT_CONFIG = dynamodb.get_item(AWS_DYNAMO_SESSION, 'mm_cosmobot', {'feature' : 'prod_config'})

    # Log config
    utils.logger.info(COSMOAGENT_CONFIG)

    main()
    