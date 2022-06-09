import os
import discord
import asyncio
import instagrapi
from loguru import logger
from datetime import datetime

# Staging
DEBUG = os.getenv('DEBUG')
LAST_STORY_ID = 0
logger.add('nicobot.log')

# Instagram vars
INSTA_USER = os.getenv('INSTA_USER')
INSTA_PWD = os.getenv('INSTA_PWD')
INSTA_CLIENT = instagrapi.Client()
INSTA_CLIENT.login(INSTA_USER, INSTA_PWD)

# Discord vars
DISCORD_BOT_TOKEN = os.getenv('INSTABOT_TOKEN')
DISCORD_INTENTS = discord.Intents.default()
DISCORD_INTENTS.members = True
DISCORD_CLIENT = discord.Client(intents=DISCORD_INTENTS)

if DEBUG:
    DISCORD_CHANNEL_ID = 983498005321764926
else:
    DISCORD_CHANNEL_ID = 983418715750142052

# Users DB
if DEBUG:
    INSTA_USERS = ['javiermilei']
    DISCORD_USERS_ID = [544386473131114517] # alturiano
else:
    INSTA_USERS = ['nftastronaut777']
    DISCORD_USERS_ID = [294616676673126401, # nicolai
                        544386473131114517, # alturiano
                        ]
# TIMEOUT
LOOP_TIMEOUT = 120

@logger.catch
def get_stories_by_user(username):
    global LAST_STORY_ID
    logger.info(f'Retrieving Stories from: {username}')

    result = {}
    user_id = INSTA_CLIENT.user_id_from_username(username)
    user_stories = INSTA_CLIENT.user_stories(user_id)

    print(LAST_STORY_ID) # debug

    if str(user_stories[-1].id) == LAST_STORY_ID:
        print('Using private API') # debug
        user_stories = INSTA_CLIENT.user_stories_v1(user_id)

    logger.info(f'{username} Number of Stories: {len(user_stories)}')
    
    for story in user_stories:
        
        pk = story.pk
        id = story.id
        url = story.thumbnail_url
        date = story.taken_at

        logger.info(f'{id} - {date}')
        result[id] = (str(url), pk, date)

    return result

@logger.catch
def update_stories(username, all_user_stories):
    global LAST_STORY_ID
    logger.info(f'Update Stories for: {username}')

    new_stories = {}
    old_id_list = []
    current_month = datetime.now().month
    current_year = datetime.now().year
    ids_file = f'{username}-{current_year}-{current_month}.txt'

    if not os.path.exists(ids_file):
        with open(ids_file, 'a') as f:
            f.write('')
    else:
        with open(ids_file, 'r') as f:
            old_id_list = f.read().splitlines()
            LAST_STORY_ID = old_id_list[-1]

    for id, info in all_user_stories.items():

        # Append new Story id
        if id not in old_id_list:
            new_stories[id] = info
            
            with open(ids_file, 'a') as f:
                f.write(f'{id}\n')
    
    # See new Stories pks
    new_stories_pks = [int(info[1]) for info in new_stories.values()]
    if new_stories_pks:
        if INSTA_CLIENT.story_seen(new_stories_pks):
            logger.info(f'Stories seen: {new_stories_pks}')
        else:
            logger.error(f'Error trying to see Stories: {new_stories_pks}')


    return new_stories


@logger.catch
async def send_message_if_story():
    
    await DISCORD_CLIENT.wait_until_ready()
    channel = DISCORD_CLIENT.get_channel(id=DISCORD_CHANNEL_ID)
        
    while not DISCORD_CLIENT.is_closed():

        for insta_user in INSTA_USERS:
            all_user_stories = get_stories_by_user(insta_user)
            new_stories = update_stories(insta_user, all_user_stories)

            for id, info in new_stories.items():

                url, pk, date = info
                
                msg = f'New Story from **{insta_user}** date: {date} url: {url}'

                for discord_user_id in DISCORD_USERS_ID:
                    discord_user =  DISCORD_CLIENT.get_user(discord_user_id)
                    msg += f' {discord_user.mention} '
                
                logger.info(msg)
                await channel.send(msg)
        
        await asyncio.sleep(LOOP_TIMEOUT)

@DISCORD_CLIENT.event
async def on_ready():
    logger.info(f'Logged in as {DISCORD_CLIENT.user.name}')

@logger.catch
def main():
    DISCORD_CLIENT.loop.create_task(send_message_if_story())
    DISCORD_CLIENT.run(DISCORD_BOT_TOKEN)

if __name__ == '__main__':
	''' Continue on Main'''
	main()


