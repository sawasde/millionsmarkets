""" Utils module containing helper functions """
# pylint: disable=no-name-in-module

import os
from utils import utils, dynamodb

#Staging
STAGING = bool(int(os.getenv('TF_VAR_COSMOBOT_STAGING')))
FROM_LAMBDA = bool(int(os.getenv('TF_VAR_COSMOBOT_FROM_LAMBDA')))

# Discord vars
DISCORD_MONITORING_HOOK_URL = os.getenv('TF_VAR_MONITORING_DISCORD_HOOK_URL')
DISCORD_MONITORING_ROLE = os.getenv('TF_VAR_MONITORING_DISCORD_ROLE')

# AWS Dynamo
AWS_DYNAMO_SESSION = dynamodb.create_session(from_lambda=FROM_LAMBDA)

@utils.logger.catch
def launch(event=None, context=None):
    """ Load configs and run once the agent"""
    # pylint: disable=unused-argument, global-statement

    utils.logger.info('Hello World!')
    """ Launch function """
    # pylint: disable=unused-argument, global-statement

    global COSMOBOT_CONFIG

    # Load config
    COSMOBOT_CONFIG = dynamodb.load_feature_value_config(   AWS_DYNAMO_SESSION,
                                                            TABLE_NAME)

    # Log path
    if not FROM_LAMBDA:
        utils.logger_path(COSMOBOT_CONFIG['log_path'])

    # Log discord
    utils.logger.info('Load Discord vars')

    # Start bot run() with threads
    threads = []

    for symbol in COSMOBOT_CONFIG['crypto_symbols']:
        runner = threading.Thread(target=run, args=(symbol,))
        threads.append(runner)
        runner.start()

    for thread in threads:
        thread.join()
