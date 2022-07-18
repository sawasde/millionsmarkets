from time import time
from loguru import logger
from utils import utils, dynamodb
import pandas as pd

@logger.catch
def get_cosmobot_time(timestamp=None):

    if not timestamp:
        timestamp = int(utils.get_timestamp(multiplier=1))
    date = utils.timestamp_to_date(timestamp)
    week = date.isocalendar()[1]
    year = date.isocalendar()[0]

    return f'{year}_{week}', week, year, date


@logger.catch
def cosmobot_historical_to_df(dyn_session, symbol, weeks=5, timestamp=None):

    dfs = []
    to_float_cols = ['ptrend', 'mtrend', 'strend', 'pclose', 'pd_limit', 'pz_limit']
    cosmo_time_now, week_now, year_now, date_now = get_cosmobot_time()

    if timestamp:
        cosmo_time_tms, week_tms, year_tms, date_tms = get_cosmobot_time(timestamp)
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
    df_result = df_result.sort_values('timestamp')
    df_result.drop(['week'], inplace=True, axis=1)
    
    # format cols
    df_result[to_float_cols] = df_result[to_float_cols].astype('float')
    df_result['timestamp'] = df_result['timestamp'].astype('int')

    return df_result

