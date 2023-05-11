""" Utils module containing helper functions """
# pylint: disable=import-error

import string
import json
import datetime as dt
import pytz
import numpy as np
import requests
from loguru import logger

@logger.catch
def logger_path(path):
    """ Set the Loguru logger path """

    logger.add(path)

@logger.catch
def hand_json(file, mode, data=None):
    """ Function to read, write json file, absolute path """

    with open(file, mode, encoding='utf-8') as f_handler:
        if mode == 'r':
            return json.loads(f_handler.read())

        data = {}
        json.dump(data, f_handler)
        return f_handler.close()


@logger.catch
def hand_file(file, mode, data=''):
    """ Function to read, write a text file """
    # pylint: disable=consider-using-f-string

    with open(file, mode, encoding='utf-8') as f_handler:
        if mode == 'r':
            return f_handler.read()

        f_handler.write('{}\r\n'.format(data))
        return f_handler.close()


@logger.catch
def num_in_text(text):
    """" check if there is a number in text """

    return any(c.isdigit() for c in text)


@logger.catch
def text_to_printable(text):
    """ return printable chars from text """

    text = [c for c in text if c in string.printable]
    return ''.join(text)


@logger.catch
def date_ago_timestmp(xtb_tms=True, **kwargs):
    """ Take time in hours, days, weeks, months ago and return the timestamp in ms """

    now = dt.datetime.now(pytz.timezone('America/Bogota'))
    date = now - dt.timedelta(**kwargs)
    result = int(dt.datetime.timestamp(date))

    if xtb_tms:
        result = result * 1000

    return result


@logger.catch
def date_oper_timestamp_and_date(tms, xtb_tms=True, oper='+', **kwargs):
    """ Add to timestamp a date """

    if xtb_tms:
        tms = int(tms / 1000)

    date = timestamp_to_date(tms)

    if oper == '-':
        result = date - dt.timedelta(**kwargs)
    elif oper == '+':
        result = date + dt.timedelta(**kwargs)

    result = int(dt.datetime.timestamp(result))

    if xtb_tms:
        result = result * 1000

    return result


@logger.catch
def get_timestamp(multiplier=1, tmz='America/Bogota'):
    """ Get current timestamp in ms """

    now = dt.datetime.now(pytz.timezone(tmz))
    result = int(dt.datetime.timestamp(now))

    return result*multiplier


@logger.catch
def round_float_num(num, dig):
    """ Take a number and round it n digits """
    # pylint: disable=consider-using-f-string

    return float('%.{}f'.format(dig) % num)


@logger.catch
def timestamp_to_date(tms, tmz='America/Bogota'):
    """ Take time in hours, days, weeks, months ago and return the timestamp in ms """

    return (dt.datetime.fromtimestamp(tms, tz=pytz.timezone(tmz)))


@logger.catch
def date_now(use_tuple=True, tmz='America/Bogota'):
    """ Return the now time according to EV TIMEZONE TZ """

    now = dt.datetime.now(pytz.timezone(tmz))
    if use_tuple:
        # y, m, d, h, minute, sec, wd, yd, i
        return now.timetuple()

    return now

@logger.catch
def date_y_m_d():
    """ Format date to YEAR MONTH and DAY separated by sep """

    today = dt.date.today()
    return today.strftime('%Y%m%d')


@logger.catch
def integrate_area_below(df_inital='', yaxis='', dx_portion=1.0):
    """ Return DataFrame with the area integrated """
    # pylint: disable=unused-variable

    df_result = df_inital.reset_index().copy()
    df_result['area'] = 0

    for i, row in df_result.iterrows():

        chunk = df_result[yaxis][0:i]

        if len(chunk) == 0:
            continue

        area = np.trapz(chunk,dx=dx_portion)
        df_result.at[i, 'area'] = area

    return df_result.copy()


@logger.catch
def discord_webhhok_send(url, username, content, embed=False, attemps=5):
    ''' send messages using Discord webhook
            embed = {"description": "desc", "title": "embed title"}
    '''
    while attemps > 0:
        data = {
            'content': content,
            'username': username,
            }

        if embed:
            data['embeds'] = [ embed ]

        headers = {
            'Content-Type': 'application/json'
        }

        result = requests.post(url, json=data, headers=headers, timeout=24)

        if 200 <= result.status_code < 300:
            break
        attemps -= 1
    return result
