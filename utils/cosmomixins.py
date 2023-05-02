""" Helper Module for cosmo code """
# pylint: disable=no-name-in-module, import-error

import os
from pathlib import Path
import pandas as pd
from utils import utils, dynamodb


@utils.logger.catch
def get_cosmobot_time(timestamp=None):
    """ Get special cosmobot time """

    if not timestamp:
        timestamp = int(utils.get_timestamp(multiplier=1))
    date = utils.timestamp_to_date(timestamp)
    week = date.isocalendar()[1]
    year = date.isocalendar()[0]

    return f'{year}_{week}', week, year, date, timestamp


@utils.logger.catch
def cosmobot_historical_to_df(dyn_session, symbol, weeks=5, timestamp=None):
    """ Get data from Dynamo nad convert it to pandas DataFrame """

    dfs = []
    week_now = get_cosmobot_time()[1]
    year_now = get_cosmobot_time()[2]

    if timestamp:
        week_tms = get_cosmobot_time(timestamp)[1]

        week_delta = week_now - week_tms

        if week_delta < 0:
            week_delta = 52 - abs(week_delta)

        weeks = 1 + week_delta

    # create array of weeks
    last_n_weeks = []

    for i in range(0, weeks):

        week_delta = week_now - i
        year_delta = year_now

        # if first days of year
        if week_delta <= 0:
            week_delta = 52 - abs(week_delta)
            year_delta -= 1

        last_n_weeks.append(f'{year_delta}_{week_delta}')

    for week in last_n_weeks:

        if timestamp:
            info = dynamodb.query_items(    dyn_session=dyn_session,
                                            table_name=f'mm_cosmobot_historical_{symbol}',
                                            pkey='week',
                                            pvalue=week,
                                            query_type='both',
                                            skey='timestamp',
                                            svalue=timestamp,
                                            scond='gte',
                                            region='sa-east-1')

        else:
            info = dynamodb.query_items(    dyn_session=dyn_session,
                                            table_name=f'mm_cosmobot_historical_{symbol}',
                                            pkey='week',
                                            pvalue=week,
                                            region='sa-east-1')

        dfs.append(pd.DataFrame(info))

    df_result = pd.concat(dfs, ignore_index=True)

    # get df format
    df_result = aux_format_dynamo_df(df_result)

    return df_result


@utils.logger.catch
def aux_format_dynamo_df(df_inital):
    """ Establish a good format DataFrame """

    to_float_cols = ['ptrend', 'mtrend', 'strend', 'pclose', 'pd_limit', 'pz_limit']
    df_result = df_inital.copy()

    # Drop week columns
    if 'week' in df_result.columns:
        df_result.drop(['week'], inplace=True, axis=1)

    # Format cols
    df_result[to_float_cols] = df_result[to_float_cols].astype('float')
    df_result['timestamp'] = df_result['timestamp'].astype('int')
    df_result = df_result.sort_values('timestamp')

    return df_result


@utils.logger.catch
def aux_format_plotter_df(df_initial, day=31, yaxis='ptrend'):
    """ Establish a good format DataFrame to plot """

    utils.logger.info('Format DF including area')

    df_initial['zero_bound'] = 0

    if len(df_initial) < 2:
        return df_initial

    day_tms = utils.date_ago_timestmp(xtb_tms=False, days=int(day))
    df_result = df_initial[df_initial['timestamp'] >= day_tms]

    # AREA STUFF
    df_result = utils.integrate_area_below(df_result, yaxis=yaxis, dx_portion=1)

    return df_result


@utils.logger.catch
def check_time(symbol, df_initial, time_diff=260):
    """ Check if the diff time is high to update local data """

    tms = int(utils.get_timestamp(multiplier=1))
    last_tms = int(df_initial['timestamp'].iloc[-1])

    diff = tms - last_tms
    utils.logger.info(f'Last tms: {utils.timestamp_to_date(last_tms)}')
    utils.logger.info(f'{symbol} Diff: {diff} seconds')

    if diff > time_diff:
        utils.logger.info(f'tms not sync. {diff} diff seconds')
        utils.logger.info(f'date: {utils.timestamp_to_date(last_tms)}')
        return False

    return True


@utils.logger.catch
def get_resource_optimized_dfs(dyn_session, symbol, static_path, weeks, time_diff=260, save=True):
    """ Main function to get data from dynamo compared and optimed to the local data """
    # pylint: disable=too-many-arguments

    if os.path.exists(static_path):
        utils.logger.info(f'Found CSV {static_path}')
        static_df = pd.read_csv(static_path)
        static_df = aux_format_dynamo_df(static_df)

        last_tms = int(static_df['timestamp'].iloc[-1])


        if check_time(symbol, static_df, time_diff):
            utils.logger.info(f'{symbol}. timestamps well coupled, using only CSV')
            df_result = static_df#.copy()

        else:
            utils.logger.info(f'{symbol}. timestamps not coupled, using dynamo with timestamp')
            dynamo_df = cosmobot_historical_to_df(dyn_session, symbol, weeks, (last_tms))

            df_result = pd.concat([static_df, dynamo_df], ignore_index=True)
            df_result = df_result.sort_values('timestamp')

    else:
        utils.logger.info(f'{symbol}. CSV not found, using pure dynamo')
        output_file = Path(static_path)
        output_file.parent.mkdir(exist_ok=True, parents=True)
        df_result = cosmobot_historical_to_df(dyn_session, symbol, weeks)

    if save:
        utils.logger.info(f'saving CSV {static_path}')
        df_result.to_csv(static_path, index=False)

    return df_result
