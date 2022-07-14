from instabot import instabot
from cosmobot import cosmoagent
from loguru import logger
import sys

if __name__ == '__main__':
    ''' Continue on Main'''

    if len(sys.argv) != 2:
        logger.info('Bad args suplied')
        sys.exit(-1)
    bot = sys.argv[1]

    if bot  == 'instabot':
        instabot.launch()
    elif bot == 'cosmoagent':
        cosmoagent.launch()
    elif bot == 'cosmobot':
        cosmoagent.launch()
    else:
        logger.info('Bot/agent not found')
        sys.exit(-1)