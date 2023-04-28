""" Run cosmoagent in a twisted loop """
# pylint: disable=no-name-in-module, import-error

from twisted.internet import task, reactor
from cosmoagent import cosmoagent as cat
from utils import utils


@utils.logger.catch
def launch():
    """ Load cosmoagent first, then the loop config and run it """
    # pylint: disable=no-member

    cat.launch()

    loop_timeout = int(cat.COSMOAGENT_CONFIG['loop_timeout'])
    loop_call = task.LoopingCall(cat.run)
    loop_call.start(loop_timeout)
    reactor.run()
