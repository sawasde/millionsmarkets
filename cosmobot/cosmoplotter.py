from loguru import logger
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
TMS_TRESSHOLD_SEC = 260


@logger.catch
def check_time(symbol, df):
    tms = int(utils.get_timestamp(multiplier=1))
    last_tms = int(df['timestamp'].iloc[-1])

    diff = tms - last_tms
    print(symbol, 'Last tms:', utils.timestamp_to_date(last_tms), 'Diff:', diff, 'seconds')

    if diff > TMS_TRESSHOLD_SEC:
        utils.logger.error(f'tms not sync. {diff} diff seconds')
        utils.logger.error(f'date: {utils.timestamp_to_date(last_tms)}')



@logger.catch
def plotter(symbol, df, days_ago=[13, 31]):

    df['zero_bound'] = 0

    if len(df) < 2:
        return

    for day in days_ago:

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
        print(symbol, day, 'PLOT SAVED')


@logger.catch
def remove_all_plots():

    for root, dirs, files in os.walk(CHART_BASE_PATH):
        for basename in files:
            filename = os.path.join(root, basename)
            
            if filename.endswith(f'.png'):
                os.remove(filename)


@logger.catch
def main(unit_test=False):
    ''' Main method '''

    # Remove previous plots
    logger.info('Removing plots ...')
    remove_all_plots()

    for symbol in COSMOAGENT_CONFIG['crypto_symbols']:

        # Get df
        logger.info(f'Get info for {symbol}')
        #df = cosmomixins.cosmobot_historical_week_to_df(AWS_DYNAMO_SESSION, symbol, 1)
        df = cosmomixins.cosmobot_historical_to_df(AWS_DYNAMO_SESSION, symbol, 1)#, utils.date_ago_timestmp(xtb_tms=False, days=int(13)))

        print(df['timestamp'].iloc[0],df['timestamp'].iloc[-1])
        return
        # Check Time
        logger.info('Checking time ...')
        check_time(symbol, df)

        # Plot
        logger.info('Plotting ...')
        plotter(symbol, df)


@logger.catch
def launch():
    global COSMOAGENT_CONFIG
    
    # Load config
    COSMOAGENT_CONFIG = dynamodb.get_item(AWS_DYNAMO_SESSION, 'mm_cosmobot', {'feature' : 'prod_config'})

    # Log config
    logger.info(COSMOAGENT_CONFIG)

    main()
    