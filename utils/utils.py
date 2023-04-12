#import dynamodb
from loguru import logger
import asyncio
import json
import datetime as dt
import pytz
import string
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
import gc


@logger.catch
def logger_path(path):
	''' the logger path'''
	logger.add(path)

# Discord Functions
async def send_discord_message_attemps(channel, msg, attemps=4, delay=4):
    try:
        for i in range(0, attemps):
            logger.info(f'Sending message. {i} Attempt')
            sent = await channel.send(msg)
            
            if sent:
                logger.info(f'Successfully sent!')
                break
            else:
                await asyncio.sleep(delay)

    except Exception as e:
        logger.error(e)


@logger.catch
def hand_json(file, mode, data={}):
    ''' Function to read, write json file, absolute path'''

    f = open(file, mode)
    if mode == 'r':
        return json.loads(f.read())
    
    json.dump(data, f)
    return f.close()


@logger.catch
def hand_file(file, mode, data=''):
    ''' Function to read, write a text file'''

    f = open(file, mode)
    if mode == 'r':
        return f.read()
    f.write('{}\r\n'.format(data))
    return f.close()


@logger.catch
def num_in_text(text):
    ''' check if there is a number in text'''
    return any(c.isdigit() for c in text)


@logger.catch
def text_to_printable(text):
    text = [c for c in text if c in string.printable]
    return ''.join(text)


@logger.catch
def date_ago_timestmp(xtb_tms=True, **kwargs):
    ''' Take time in hours, days, weeks, months ago and return the timestamp in ms'''
    now = dt.datetime.now(pytz.timezone('America/Bogota'))
    date = now - dt.timedelta(**kwargs)
    result = int(dt.datetime.timestamp(date))

    if xtb_tms:
        result = result * 1000

    return result


@logger.catch
def date_oper_timestamp_and_date(tms, xtb_tms=True, oper='+', **kwargs):
    '''Add to timestamp a date'''
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
def get_timestamp(multiplier=1):
    ''' Get current timestamp in ms'''
    now = dt.datetime.now(pytz.timezone('America/Bogota'))
    result = int(dt.datetime.timestamp(now))

    return result*multiplier



@logger.catch
def round_float_num(num, dig):
    return float('%.{}f'.format(dig) % num)


@logger.catch
def timestamp_to_date(tms, tz='America/Bogota'):
    ''' Take time in hours, days, weeks, months ago and return the timestamp in ms'''
    return (dt.datetime.fromtimestamp(tms, tz=pytz.timezone(tz)))


@logger.catch
def date_now(tp=True, tz='America/Bogota'):
    ''' Return the now time according to EV TIMEZONE TZ '''
    now = dt.datetime.now(pytz.timezone(tz))
    if tp:
        # y, m, d, h, minute, sec, wd, yd, i 
        return now.timetuple()
    else:
        return now

@logger.catch
def date_y_m_d():
    ''' Format date to YEAR MONTH and DAY separated by sep'''
    
    today = dt.date.today()
    return today.strftime('%Y%m%d')


@logger.catch
def integrate_area_below(df='', yaxis='', dx=1.0):
    ''' Return df with the area iterated'''

    df_result = df.reset_index().copy()
    df_result['area'] = 0

    for i, row in df_result.iterrows():
        
        chunk = df_result[yaxis][0:i]

        if len(chunk) == 0:
            continue
        
        area = np.trapz(chunk,dx=dx)
        df_result.at[i, 'area'] = area

    return df_result.copy()

