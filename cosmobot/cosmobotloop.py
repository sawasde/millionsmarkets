""" Run cosmoagent in a cron job """
# pylint: disable=no-name-in-module, import-error

import os
from cosmobot import cosmobot as cbot
from utils import utils


@utils.logger.catch
def run():
    """ Loop Run of cosmobot """
    utils.logger.info('Run Cosmobot on CRYPTOS')
    cbot.SYMBOL_TYPE = 'CRYPTO'
    cbot.launch(event='set_log_path')

    utils.logger.info('Run Cosmobot on STOCKS')
    cbot.SYMBOL_TYPE = 'STOCK'
    cbot.launch()

    utils.logger.info('Run Cosmobot on ETFs')
    cbot.SYMBOL_TYPE = 'ETF'
    cbot.launch()



@utils.logger.catch
def launch():
    """ Load cosmoagent first, then the loop config and run it """
    # pylint: disable=no-member

    cbot.launch(event='first_launch')

    cron_expr = cbot.COSMOBOT_CONFIG['cron_expression']
    python_cmd = 'from cosmobot import cosmobotloop as cbl; cbl.run()'
    command = f"cd /millionsmarkets && sudo python3 -c '{python_cmd}'"
    user = 'root'
    cron_file = '/etc/crontab'

    utils.logger.info('Creating CRON Job')
    os.system(f'sudo echo "{cron_expr} {user} {command}" >> {cron_file}')

if __name__ == "__main__":
    run()
