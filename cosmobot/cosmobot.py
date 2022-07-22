import os
from re import S
import discord
import asyncio
from utils import utils, dynamodb
from cosmobot import cosmoagent, cosmomixins
from binance.client import Client

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

# Binance variables
BIN_API_KEY = os.environ['BIN_API_KEY']
BIN_API_SECRET = os.environ['BIN_API_SECRET']
BIN_CLIENT = None
ALL_CRYPTO_PRICE = []


@utils.logger.catch
def check_cosmo_call(symbol, ptrend, mtrend, strend, pd_limit, pz_limit, pclose):
    global COSMO_SYMBOLS_COUNTER

    curr_area = COSMO_SYMBOLS_DFS[symbol]['area'].iloc[-1]
    limit_area = float(COSMO_SYMBOLS_PARAMETERS[symbol]['limit_area'])

    trade = None

    # 1st check: LongTerm trend
    if abs(curr_area) > limit_area:
        utils.logger.info(f'1st check passed curr_area: {curr_area} limit_area: {limit_area}')
        # 2nd check: bear or bull market
        
        # Bull market
        if curr_area > 0:
            limit_mtrend = int(COSMO_SYMBOLS_PARAMETERS[symbol]['bull_mtrend'])
            utils.logger.info(f'2nd check passed BULL market: {limit_mtrend}')
        # Bear market
        else:
            limit_mtrend = int(COSMO_SYMBOLS_PARAMETERS[symbol]['bear_mtrend'])
            utils.logger.info(f'2nd check passed BEAR market: {limit_mtrend}')
        
        # 3rd check: mtrend limit reached BUY or SELL
        # BUY
        if mtrend > 0:
            if mtrend > (limit_mtrend):
                utils.logger.info(f'3rd check passed SELL mtrend: {mtrend}')
                trade = 'SELL'
        # SELL
        else:
            if mtrend < (- limit_mtrend):
                utils.logger.info(f'3rd check passed BUY mtrend: {mtrend}')
                trade = 'BUY'

    return trade


@utils.logger.catch
def update_cosmo_parameters(symbol):
    global COSMO_SYMBOLS_PARAMETERS
    
    symbol_parameter_item = dynamodb.get_item(   AWS_DYNAMO_SESSION, 
                                                TABLE_NAME,
                                                {'feature' : f'{symbol}_parameters'})
    symbol_df = COSMO_SYMBOLS_DFS[symbol]
    COSMO_SYMBOLS_PARAMETERS[symbol] = symbol_parameter_item


@utils.logger.catch
def update_cosmo_dfs(symbol):
    global COSMO_SYMBOLS_DFS
    
    csv_path = CSV_ASSET_PATH.format(SYMBOLS_BASE_PATH, symbol)
    symbol_df = cosmomixins.get_resource_optimized_dfs(AWS_DYNAMO_SESSION, symbol, csv_path, 5, 521)
    symbol_df = cosmomixins.aux_format_plotter_df(symbol_df, 31)

    COSMO_SYMBOLS_DFS[symbol] = symbol_df


@utils.logger.catch
async def send_message_if_alert():
    global COSMOBOT_CONFIG
    
    await DISCORD_CLIENT.wait_until_ready()
    channel = DISCORD_CLIENT.get_channel(id=int(COSMOBOT_CONFIG['discord_channel_id']))
    guild =  DISCORD_CLIENT.get_guild(id=int(COSMOBOT_CONFIG['discord_server_id']))
        
    while not DISCORD_CLIENT.is_closed():

        for symbol in COSMOBOT_CONFIG['crypto_symbols']:
            
            minute = utils.date_now()[4]

            # cosmo check every x minutes
            if minute % COSMOBOT_CONFIG['cosmo_check_minutes'] == 0:
                
                # Get config again
                COSMOBOT_CONFIG = dynamodb.load_feature_value_config(   AWS_DYNAMO_SESSION, 
                                                                        TABLE_NAME, 
                                                                        DEBUG )
                update_cosmo_dfs(symbol)
                update_cosmo_parameters(symbol)

            # populate global memory dicts in 1st time run
            if (not COSMO_SYMBOLS_DFS) or (not COSMO_SYMBOLS_PARAMETERS):

                update_cosmo_dfs(symbol)
                update_cosmo_parameters(symbol)

            # check for a trading call
            symbol_cosmo_info = cosmoagent.get_planet_trend(symbol, BIN_CLIENT)

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
                msg = f'{cosmo_call} **{symbol}**\n'
                msg += f'Mean trend: {mtrend}\n'
                msg += f'Longterm trend: {area}\n'
                msg += f'Limit price: ${pzlimit}\n'
                msg += f'Current price: ${pclose}\n'

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


@utils.logger.catch
def launch():
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
    DISCORD_CLIENT.loop.create_task(send_message_if_alert())
    DISCORD_CLIENT.run(DISCORD_BOT_TOKEN)
