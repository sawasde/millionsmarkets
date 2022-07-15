from time import time
from loguru import logger
from utils import utils, dynamodb
import pandas as pd

@logger.catch
def get_cosmobot_time():

    timestamp = int(utils.get_timestamp(multiplier=1))
    date = utils.timestamp_to_date(timestamp)
    week = date.isocalendar()[1]
    year = date.isocalendar()[0]

    return f'{year}_{week}', week, year, timestamp


@logger.catch
def cosmobot_historical_to_df(dyn_session, symbol, weeks=5, timestamp=None):

    dfs = []

    cosmo_time = get_cosmobot_time()
    week = cosmo_time[1]
    year = cosmo_time[2]
    last_five_weeks = [f'{year}_{week - i}' for i in range(0, weeks)]

    for week in last_five_weeks:
#dyn_session, table_name, pkey, pvalue, type='partition', pcond='eq', skey=None, svalue=None, scond='eq', region='us-east-1'
        if timestamp:
            info = dynamodb.query_items(    dyn_session=dyn_session, 
                                            table_name=f'mm_cosmobot_historical_{symbol}',
                                            pkey='week',
                                            pvalue=week,
                                            pcond='eq',
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
    df_result.drop(['week'], inplace=True, axis=1)
    df_result = df_result.apply(pd.to_numeric, downcast='float')
    df_result = df_result.sort_values('timestamp')

    return df_result

