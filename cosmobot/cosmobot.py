import os
import discord

from utils import utils, dynamodb

#Staging
DEBUG = bool(int(os.getenv('COSMOBOT_DEBUG')))

# Discord vars
DISCORD_BOT_TOKEN = os.getenv('COSMOBOT_TOKEN')
DISCORD_INTENTS = discord.Intents.default()
DISCORD_INTENTS.members = True
DISCORD_CLIENT = discord.Client(intents=DISCORD_INTENTS)

# AWS Dynamo
AWS_DYNAMO_SESSION = dynamodb.create_session()

# General vars
COSMOBOT_CONFIG = {}

@utils.logger.catch
def launch():
    global COSMOBOT_CONFIG
    
    # Load config
    COSMOBOT_CONFIG = dynamodb.load_feature_value_config(AWS_DYNAMO_SESSION, 'mm_cosmobot', DEBUG)

    # Log path
    utils.logger_path(COSMOBOT_CONFIG['log_path'])

    # Log config
    utils.logger.info(COSMOBOT_CONFIG)

    # Discord initialize
    #DISCORD_CLIENT.loop.create_task(send_message_if_story())
    DISCORD_CLIENT.run(DISCORD_BOT_TOKEN)


@DISCORD_CLIENT.event
async def on_ready():

    utils.logger.info(f'Logged in as {DISCORD_CLIENT.user.name}')
    utils.logger.info(COSMOBOT_CONFIG)
    
    await DISCORD_CLIENT.wait_until_ready()
    channel = DISCORD_CLIENT.get_channel(id=int(COSMOBOT_CONFIG['discord_channel_id']))

    guild = DISCORD_CLIENT.get_guild(int(COSMOBOT_CONFIG['discord_server_id']))
    role = guild.get_role(int(COSMOBOT_CONFIG['discord_role_ids'][0]))

    print(role.mention)
    a = await channel.send(role.mention)
