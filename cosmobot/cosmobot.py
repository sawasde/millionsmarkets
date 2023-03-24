import os
from re import S
from statistics import mean
import discord
import asyncio
from utils import utils, dynamodb
from cosmobot import cosmoagent, cosmomixins
from binance.client import Client
import numpy as np

#Staging
DEBUG = bool(int(os.getenv('COSMOBOT_DEBUG')))

# Discord vars
DISCORD_BOT_TOKEN = os.getenv('COSMOBOT_TOKEN')
DISCORD_INTENTS = discord.Intents.default()
DISCORD_INTENTS.members = True
DISCORD_CLIENT = discord.Client(intents=DISCORD_INTENTS)

# AWS Dynamo
AWS_DYNAMO_SESSION = dynamodb.create_session()
TABLE_NAME = 'mm_cosmobot'

# General vars
COSMOBOT_CONFIG = {}
SYMBOLS_BASE_PATH = 'cosmobot/assets/'
CSV_ASSET_PATH = '{}{}.csv'
COSMO_SYMBOLS_PARAMETERS = {}
COSMO_SYMBOLS_DFS = {}
COSMO_SYMBOLS_SIGNAL = {}

# Binance variables
BIN_API_KEY = os.environ['BIN_API_KEY']
BIN_API_SECRET = os.environ['BIN_API_SECRET']
BIN_CLIENT = None
ALL_CRYPTO_PRICE = []


@utils.logger.catch
def check_cosmo_call(symbol, ptrend, mtrend, strend, pd_limit, pz_limit, pclose):
    global COSMO_SYMBOLS_SIGNAL

    curr_area = COSMO_SYMBOLS_DFS[symbol]['area'].iloc[-1]
    limit_area = float(COSMO_SYMBOLS_PARAMETERS[symbol]['limit_area'])
    # filter mtrend
    trade = None

    # if current signal already sent, wait x minutes to reset
    if COSMO_SYMBOLS_SIGNAL[symbol]:
        return None

    # 1st check: LongTerm trend
    if abs(curr_area) > limit_area:
        utils.logger.info(f'1st check passed curr_area: {curr_area} limit_area: {limit_area}')
   
        bull_limit_mtrend = int(COSMO_SYMBOLS_PARAMETERS[symbol]['bull_mtrend'])
        bear_limit_mtrend = int(COSMO_SYMBOLS_PARAMETERS[symbol]['bear_mtrend'])

        # 2nd check: mtrend limit reached BUY or SELL
        # BUY
        if mtrend < (bear_limit_mtrend):
            utils.logger.info(f'2nd check passed BUY mtrend: {mtrend}')
            trade = 'BUY' if not COSMO_SYMBOLS_SIGNAL[symbol] else None
            COSMO_SYMBOLS_SIGNAL[symbol] = True

        # SELL
        if mtrend > (bull_limit_mtrend):
            utils.logger.info(f'2nd check passed SELL mtrend: {mtrend}')
            trade = 'SELL' if not COSMO_SYMBOLS_SIGNAL[symbol] else None
            COSMO_SYMBOLS_SIGNAL[symbol] = True

    return trade

@utils.logger.catch
def find_peaks(initial_array, order=8888, type='max'):
    peaks = []
    arrays = np.array_split(np.flip(initial_array), order)

    if type == 'max':
        for arr in arrays:
            maxi = arr.max()
            if maxi < 0:
                continue
            else: 
                peaks.append(maxi)
        return np.array(peaks)
    else:
        for arr in arrays:
            mini = arr.min()
            if mini > 0:
                continue
            else:
                peaks.append(mini)
        return np.array(peaks)


@utils.logger.catch
def update_cosmo_parameters(symbol):
    global COSMO_SYMBOLS_PARAMETERS
    utils.logger.info('Update cosmo parameters')
    
    symbol_parameter_item = dynamodb.get_item(   AWS_DYNAMO_SESSION, 
                                                TABLE_NAME,
                                                {'feature' : f'{symbol}_parameters'})
    symbol_df = COSMO_SYMBOLS_DFS[symbol]

    # order n
    order_n = int(symbol_parameter_item['order_mtrend'])

    mtrend_array = symbol_df['mtrend'].to_numpy()
    # Find local peaks
    mtrend_maxima = find_peaks(mtrend_array, order=order_n, type='max')
    mtrend_minima = find_peaks(mtrend_array, order=order_n, type='min')

    print('MAXI', mtrend_maxima)
    print('MINI', mtrend_minima)

    maxima_mean = mtrend_maxima.mean()
    minima_mean = mtrend_minima.mean()

    symbol_parameter_item['bull_mtrend']= int(maxima_mean)
    symbol_parameter_item['bear_mtrend'] = int(minima_mean)

    # Log parameters
    utils.logger.info(f'parameters max: {maxima_mean} min {minima_mean}')
    # Put it on memory
    COSMO_SYMBOLS_PARAMETERS[symbol] = symbol_parameter_item

    # Put it on dynamo
    dynamodb.put_item(  AWS_DYNAMO_SESSION,
                        TABLE_NAME,
                        {'feature' : f'{symbol}_parameters',
                        'value' : symbol_parameter_item})


@utils.logger.catch
def update_cosmo_dfs(symbol):
    global COSMO_SYMBOLS_DFS
    utils.logger.info('Update cosmo DFs')
    
    csv_path = CSV_ASSET_PATH.format(SYMBOLS_BASE_PATH, symbol)
    symbol_df = cosmomixins.get_resource_optimized_dfs(AWS_DYNAMO_SESSION, symbol, csv_path, 5, 521)
    symbol_df = cosmomixins.aux_format_plotter_df(symbol_df, 31)

    COSMO_SYMBOLS_DFS[symbol] = symbol_df

def prepare_msg(call, symbol, mtrend, area, pzlimit, pclose):
    # Prepare message
    msg = f'{call} **{symbol}**\n'
    msg += f'Mean trend: {mtrend}\n'
    msg += f'Longterm trend: {area}\n'
    msg += f'Limit price: ${pzlimit}\n'
    msg += f'Current price: ${pclose}\n'
    return msg

@utils.logger.catch
async def send_message_if_alert():
    global COSMOBOT_CONFIG
    global COSMO_SYMBOLS_SIGNAL
    
    await DISCORD_CLIENT.wait_until_ready()
    channel = DISCORD_CLIENT.get_channel(int(COSMOBOT_CONFIG['discord_channel_id']))
    guild =  DISCORD_CLIENT.get_guild(int(COSMOBOT_CONFIG['discord_server_id']))
        
    while not DISCORD_CLIENT.is_closed():

        for symbol in COSMOBOT_CONFIG['crypto_symbols']:
            
            minute = utils.date_now()[4]

            # cosmo check every x minutes
            if minute % COSMOBOT_CONFIG['check_df_minutes'] == 0:
                
                # Get config again
                COSMOBOT_CONFIG = dynamodb.load_feature_value_config(   AWS_DYNAMO_SESSION, 
                                                                        TABLE_NAME, 
                                                                        DEBUG )
                # Update Stuff
                update_cosmo_dfs(symbol)
                update_cosmo_parameters(symbol)
                COSMO_SYMBOLS_SIGNAL[symbol] = False

            # populate global memory dicts in 1st time run
            if (not COSMO_SYMBOLS_DFS) or (not COSMO_SYMBOLS_PARAMETERS):

                # Update Stuff
                update_cosmo_dfs(symbol)
                update_cosmo_parameters(symbol)
                COSMO_SYMBOLS_SIGNAL[symbol] = False

            # check for a trading call
            symbol_cosmo_info = cosmoagent.get_planet_trend(symbol, BIN_CLIENT)
            
            if not symbol_cosmo_info[1]:
                continue

            if DEBUG:
                print(symbol_cosmo_info)

            # send message for trading call
            cosmo_call = check_cosmo_call(*symbol_cosmo_info)
            if cosmo_call:
                
                # Get Cosmo Variables
                mtrend = symbol_cosmo_info[2]
                pzlimit = symbol_cosmo_info[5]
                pclose = symbol_cosmo_info[6]
                area = COSMO_SYMBOLS_DFS[symbol]['area'].iloc[-1]
                area = '{:.2e}'.format(area)

                # Prepare message
                msg = prepare_msg(cosmo_call, symbol, mtrend, area, pzlimit, pclose)

                # mention roles
                discord_role =  guild.get_role(int(COSMOBOT_CONFIG['discord_role_id']))
                msg += f'{discord_role.mention}'
                
                # send message. Try 4 times
                if DEBUG:
                    utils.logger.info(msg)
                await utils.send_discord_message_attemps(channel, msg, 4)
        
        # loop timeout
        await asyncio.sleep(int(COSMOBOT_CONFIG['loop_timeout']))


@DISCORD_CLIENT.event
async def on_ready():
    utils.logger.info(f'Logged in as {DISCORD_CLIENT.user.name}')

async def on_loop():
    async with DISCORD_CLIENT:
        DISCORD_CLIENT.loop.create_task(send_message_if_alert())
        await DISCORD_CLIENT.start(DISCORD_BOT_TOKEN)


@utils.logger.catch
def loop_launch():
    global COSMOBOT_CONFIG
    global BIN_CLIENT
    
    # Load config
    COSMOBOT_CONFIG = dynamodb.load_feature_value_config(AWS_DYNAMO_SESSION, 'mm_cosmobot', DEBUG) 

    # Log path
    utils.logger_path(COSMOBOT_CONFIG['log_path'])

    # Log config
    utils.logger.info(COSMOBOT_CONFIG)

    #Binance
    utils.logger.info('AUTH BINANCE')
    BIN_CLIENT = Client(BIN_API_KEY, BIN_API_SECRET)
    
    # Discord initialize
    asyncio.run(on_loop())
