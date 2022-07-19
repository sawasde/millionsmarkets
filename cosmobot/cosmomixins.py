from time import time
from loguru import logger
import pandas as pd
import os
from utils import utils, dynamodb


@logger.catch
def get_cosmobot_time(timestamp=None):

    if not timestamp:
        timestamp = int(utils.get_timestamp(multiplier=1))
    date = utils.timestamp_to_date(timestamp)
    week = date.isocalendar()[1]
    year = date.isocalendar()[0]

    return f'{year}_{week}', week, year, date, timestamp


@logger.catch
def cosmobot_historical_to_df(dyn_session, symbol, weeks=5, timestamp=None):

    dfs = []
    cosmo_time_now, week_now, year_now, date_now, tms_now = get_cosmobot_time()

    if timestamp:
        cosmo_time_tms, week_tms, year_tms, date_tms, tms_tms = get_cosmobot_time(timestamp)
        date_days_delta = abs(date_now - date_tms).days
        weeks = 1 + (date_days_delta // 7)

    # create array of weeks
    last_n_weeks = []

    for i in range(0, weeks):

        week_delta = week_now - i
        year_delta = year_now

        # if first days of year
        if week_delta <= 0:
            week_delta = 52 - abs(week_delta)
            year_delta = year_now -1

        last_n_weeks.append(f'{year_delta}_{week_delta}')

    for week in last_n_weeks:

        if timestamp:
            info = dynamodb.query_items(    dyn_session=dyn_session, 
                                            table_name=f'mm_cosmobot_historical_{symbol}',
                                            pkey='week',
                                            pvalue=week,
                                            type='both',
                                            skey='timestamp',
                                            svalue=timestamp,
                                            scond='gte')

        else: 
            info = dynamodb.query_items(    dyn_session=dyn_session, 
                                            table_name=f'mm_cosmobot_historical_{symbol}',
                                            pkey='week',
                                            pvalue=week)

        dfs.append(pd.DataFrame(info))

    df_result = pd.concat(dfs, ignore_index=True)
    
    # get df format
    df_result = aux_format_dynamo_df(df_result)

    return df_result


@logger.catch
def aux_format_dynamo_df(df):

    to_float_cols = ['ptrend', 'mtrend', 'strend', 'pclose', 'pd_limit', 'pz_limit']
    df_result = df.copy()
    
    # Drop week columns
    df_result.drop(['week'], inplace=True, axis=1)

    # Format cols
    df_result[to_float_cols] = df_result[to_float_cols].astype('float')
    df_result['timestamp'] = df_result['timestamp'].astype('int')
    df_result = df_result.sort_values('timestamp')

    return df_result



@logger.catch
def check_time(symbol, df, time_diff=260):
    tms = int(utils.get_timestamp(multiplier=1))
    last_tms = int(df['timestamp'].iloc[-1])

    diff = tms - last_tms
    logger.info(symbol, 'Last tms:', utils.timestamp_to_date(last_tms), 'Diff:', diff, 'seconds')

    if diff > time_diff:
        logger.error(f'tms not sync. {diff} diff seconds')
        logger.error(f'date: {utils.timestamp_to_date(last_tms)}')
        return False
    
    return True


@logger.catch
def get_resource_optimized_dfs(dyn_session, symbol, static_path, weeks, save_csv=True):
    
    if os.path.exists(static_path):
        logger.info(f'Found CSV {static_path}')
        static_df = pd.read_csv(static_path)
        last_tms = static_df['timestamp'].iloc[-1]

        if check_time(symbol, static_df):
            logger.info(f'{symbol}. timestamps well coupled, using only CSV')
            df_result = static_df.copy()
        
        else:
            logger.info(f'{symbol}. timestamps not coupled, using dynamo with timestamp')
            dynamo_df = cosmobot_historical_to_df(dyn_session, symbol, weeks, last_tms)

            df_result = pd.concat([static_df, dynamo_df], ignore_index=True)
            df_result = df_result.sort_values('timestamp')

    else:
        logger.info(f'{symbol}. CSV not found, using pure dynamo')
        df_result = cosmobot_historical_to_df(dyn_session, symbol, weeks)
    
    if save_csv:
        logger.info(f'saving CSV {static_path}')
        df_result.to_csv(static_path, index=False)

    return df_result
