#import dynamodb
from loguru import logger
import asyncio

# AWS Dynamo
# AWS_DYNAMO_SESSION = dynamodb.create_session()


# Discord Functions
async def send_discord_message_attemps(channel, msg, attemps=4, logger=logger, delay=4):
    try:
        print('hereee')
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
