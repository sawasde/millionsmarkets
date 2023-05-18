""" Utils module containing helper functions """
# pylint: disable=no-name-in-module

from utils import utils

@utils.logger.catch
def launch(event=None, context=None):
    """ Load configs and run once the agent"""
    # pylint: disable=unused-argument, global-statement

    utils.logger.info('Hello World!')
