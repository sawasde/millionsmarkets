import os
import discord
import asyncio
import instagrapi
import time
from loguru import logger
from datetime import datetime
from utils import dynamodb, utils

# Staging
DEBUG = os.getenv('INSTABOT_DEBUG')
LAST_STORY_ID = 0

# Instagram vars
INSTA_USER = os.getenv('INSTA_USER')
INSTA_PWD = os.getenv('INSTA_PWD')

# Discord vars
DISCORD_BOT_TOKEN = os.getenv('INSTABOT_TOKEN')
DISCORD_INTENTS = discord.Intents.default()
DISCORD_INTENTS.members = True
DISCORD_CLIENT = discord.Client(intents=DISCORD_INTENTS)

# AWS Dynamo
AWS_DYNAMO_SESSION = dynamodb.create_session()

# Genral vars
INSTABOT_CONFIG = {}

@logger.catch
def instagram_login():
    global INSTA_CLIENT
    logger.info(f'Log in Instagram')
    
    INSTA_CLIENT = instagrapi.Client()
    INSTA_CLIENT.login(INSTA_USER, INSTA_PWD)
    time.sleep(44)


@logger.catch
def load_config():
    logger.info(f'Load Config dict')
   
    if DEBUG:
        return dynamodb.get_item(AWS_DYNAMO_SESSION, 'mm_instabot', {'feature' : 'test_config'})
    else:
        return dynamodb.get_item(AWS_DYNAMO_SESSION, 'mm_instabot', {'feature' : 'prod_config'})


@logger.catch
def get_stories_by_user(username):
    global LAST_STORY_ID
    logger.info(f'Retrieving Stories from: {username}')
    result = {}

    try:
        user_id = INSTA_CLIENT.user_id_from_username(username)
        user_stories = INSTA_CLIENT.user_stories(user_id)

        if user_stories:
            if str(user_stories[-1].id) == LAST_STORY_ID:
                user_stories = INSTA_CLIENT.user_stories_v1(user_id)

        logger.info(f'{username} Number of Stories: {len(user_stories)}')
        
        for story in user_stories:
            
            pk = story.pk
            id = story.id
            url = story.thumbnail_url
            date = story.taken_at

            logger.info(f'{id} - {date}')
            result[id] = (str(url), pk, date)
    
    except Exception as e:
        result = {}
        logger.error(e)
    
    finally:
        return result

def see_stories(new_stories):
    stories_seen = False
    try:
        # See new Stories pks
        new_stories_pks = [int(info[1]) for info in new_stories.values()]
        if new_stories_pks:
            if INSTA_CLIENT.story_seen(new_stories_pks):
                logger.info(f'Stories seen: {new_stories_pks}')
            stories_seen = True

    except Exception as e:
        logger.error(e)
        stories_seen = False
        if 'login_required' in str(e):
            instagram_login()

    finally:
        return stories_seen


def update_stories(username, all_user_stories):
    global LAST_STORY_ID
    logger.info(f'Update Stories for: {username}')
    new_stories = {}

    try:
        current_month = datetime.now().month
        current_year = datetime.now().year

        stories_log = dynamodb.get_item( AWS_DYNAMO_SESSION, 
                                        'mm_instabot', 
                                        {'feature': f'{username}_stories_{current_year}_{current_month}'})

        if stories_log:
            LAST_STORY_ID = stories_log[-1]
        else:
            stories_log = []

        for id, info in all_user_stories.items():

            # Append new Story id
            if id not in stories_log:
                new_stories[id] = info
                stories_log.append(id)
        
        # See Stories
        stories_seen = see_stories(new_stories)

        # If story are correctly seen then instagram is ok, then it is saved in DB
        if stories_seen:
            # Put it to dynamo DB
            dynamodb.put_item(  AWS_DYNAMO_SESSION, 
                                'mm_instabot', 
                                {'feature' : f'{username}_stories_{current_year}_{current_month}',
                                'value' : stories_log})
    
    except Exception as e:
        logger.error(e)
        if 'login_required' in str(e):
            instagram_login()

    finally:
        return new_stories


@logger.catch
async def send_message_if_story():
    global INSTABOT_CONFIG
    
    await DISCORD_CLIENT.wait_until_ready()
    channel = DISCORD_CLIENT.get_channel(id=int(INSTABOT_CONFIG['discord_channel_id']))
    guild =  DISCORD_CLIENT.get_guild(id=int(INSTABOT_CONFIG['discord_server_id']))
        
    while not DISCORD_CLIENT.is_closed():
        INSTABOT_CONFIG = load_config()
        await asyncio.sleep(int(INSTABOT_CONFIG['loop_timeout']))

        for insta_user in INSTABOT_CONFIG['insta_target_users']:
            all_user_stories = get_stories_by_user(insta_user)
            new_stories = update_stories(insta_user, all_user_stories)

            for id, info in new_stories.items():

                url, pk, date = info
                
                msg = f'New Story from **{insta_user}** date: {date} url: {url}'

                # mention users
                #for discord_user_id in INSTABOT_CONFIG['discord_users_ids']:
                #    discord_user =  DISCORD_CLIENT.get_user(int(discord_user_id))
                #    msg += f' {discord_user.mention} '
                
                # mention roles
                for discord_role_id in INSTABOT_CONFIG['discord_role_ids']:
                    discord_role =  guild.get_role(int(discord_role_id))
                    msg += f' {discord_role.mention} '
                
                # send message. Try 4 times
                logger.info(msg)
                await utils.send_discord_message_attemps(channel, msg, 4, logger)


@DISCORD_CLIENT.event
async def on_ready():
    logger.info(f'Logged in as {DISCORD_CLIENT.user.name}')


@logger.catch
def launch():
    global INSTABOT_CONFIG
    
    # Load config
    INSTABOT_CONFIG = load_config()

    # Log path
    logger.add(INSTABOT_CONFIG['log_path'])

    #login to instagram
    instagram_login()

    # Log config
    logger.info(INSTABOT_CONFIG)

    # Discord initialize
    DISCORD_CLIENT.loop.create_task(send_message_if_story())
    DISCORD_CLIENT.run(DISCORD_BOT_TOKEN)

