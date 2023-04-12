from cosmoagent import cosmoagent as cat
from utils import utils
from twisted.internet import task, reactor


@utils.logger.catch
def launch():
    cat.launch()

    loop_timeout = int(cat.COSMOAGENT_CONFIG['loop_timeout'])
    loop_call = task.LoopingCall(cat.run)
    loop_call.start(loop_timeout)
    reactor.run()