""" Run cosmoagent in a twisted loop """
# pylint: disable=no-name-in-module, import-error

from twisted.internet import task, reactor
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

    loop_timeout = int(cbot.COSMOBOT_CONFIG['loop_timeout'])
    loop_call = task.LoopingCall(run)
    loop_call.start(loop_timeout)
    reactor.run()
