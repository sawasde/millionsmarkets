""" Run cosmoagent in a cron job """
# pylint: disable=no-name-in-module, import-error

import os
from cosmobot import cosmobot as cbot
from utils import utils


@utils.logger.catch
def run():
    """ Loop Run of cosmobot """
    utils.logger.info('Run Cosmobot on cryptos')
    cbot.SYMBOL_TYPE = 'CRYPTO'
    cbot.launch()

    utils.logger.info('Run Cosmobot on stocks')
    cbot.SYMBOL_TYPE = 'STOCK'
    cbot.launch()


@utils.logger.catch
def launch():
    """ Load cosmoagent first, then the loop config and run it """
    # pylint: disable=no-member

    cbot.launch(event='first_launch')

    cron_expr = cbot.COSMOBOT_CONFIG['cron_expression']
    command = "cd /millionsmarkets && sudo python3 -c 'from cosmobot import cosmobotloop.py as cbl; cbl.run()'"
    user = 'root'

    utils.logger.info('Creating CRON Job')
    os.system(f'sudo echo "{cron_expr} {user} {command}" >> /etc/crontab')

if __name__ == "__main__":
    run()
