""" Custom Indicators module """
# pylint: disable=no-name-in-module

from utils import utils

@utils.logger.catch
def planets_volume(df_inital, return_decimal=5, trend_type='pure'):
    '''need an OCHLV candles dataframe. Return the tendency, normally a 4 day data must be input'''

    df_res = df_inital.copy()
    df_res.reset_index(inplace=True)

    df_res['candle_corpus'] = df_res['close'] - df_res['open']
    df_res['mass'] = df_res['candle_corpus'] * df_res['volume']
    df_res['distance'] = df_res.index[::-1] + 1

    df_res['gravity'] = df_res['mass'] / (df_res['distance'] * df_res['distance'])
    df_res['abs_gravity'] = df_res['gravity'].abs()

    # gravity SUM
    total_gravity = df_res['gravity'].sum()

    # trend definition
    if trend_type == 'pure':
        trend = total_gravity
    else:
        # trend direction
        direction = 1 if total_gravity >= 0 else -1

        # trend intensity
        if trend_type == 'mean':
            intensity = abs(df_res['gravity'].iloc[-1]) / (df_res['abs_gravity'].mean())

        elif trend_type == 'sum':
            intensity = abs(df_res['gravity'].iloc[-1]) / abs(total_gravity)

        trend = intensity * direction

    # limits
    zero_limit = df_res['open'].iloc[-1]

    # change direction limit
    df_ch_dir = df_res.iloc[:-1]
    ch_dir_gravity = df_ch_dir['gravity'].sum()

    ch_dir_vol = df_ch_dir['volume'].mean() - df_ch_dir['volume'].std()

    if df_res['volume'].iloc[-1] > ch_dir_vol:
        ch_dir_vol = df_res['volume'].iloc[-1]

    ch_dir_corpus = abs(ch_dir_gravity) / ch_dir_vol


    if ch_dir_gravity >= 0:
        dir_limit = df_res['open'].iloc[-1] - ch_dir_corpus
    else:
        dir_limit = df_res['open'].iloc[-1] + ch_dir_corpus

    return     utils.round_float_num(trend, return_decimal), \
            utils.round_float_num(df_res['close'].iloc[-1], return_decimal), \
            utils.round_float_num(dir_limit, return_decimal), \
            utils.round_float_num(zero_limit, return_decimal)
