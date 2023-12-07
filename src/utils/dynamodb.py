""" AWS Dynamo helper module """
# pylint: disable=no-name-in-module, import-error

from decimal import Decimal
import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from utils import utils

@utils.logger.catch
def load_feature_value_config(dyn_session, table, value='config', staging=True):
    """ Load feature(key) value(value) config table """

    if staging:
        table += '_staging'

    utils.logger.info(f'Load Config for {table} {value}')
    return get_item(dyn_session, table, {'feature' : value})


@utils.logger.catch
def create_session(from_lambda=False):
    """ Create AWS boto3 session """

    if from_lambda:
        return boto3.Session()

    return boto3.Session(
                        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                        region_name='sa-east-1'
                        )

@utils.logger.catch
def get_item(dyn_session, table_name, key, region='sa-east-1'):
    """ Get a single item from a table given a key """

    dynamodb = dyn_session.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)

    response = table.get_item(Key=key)

    if 'Item' in response:
        return response['Item']['value']

    return None


@utils.logger.catch
def put_item_from_dict(dyn_session, table_name, data, staging, region='sa-east-1'):
    """ Put Item to table given a dict """

    item = json.loads(json.dumps(data), parse_float=Decimal)

    if staging:
        table_name += '_staging'

    put_item(dyn_session,
             table_name,
             item,
             region=region)


@utils.logger.catch
def put_item(dyn_session, table_name, item, region='sa-east-1'):
    """ Put Item to table given a key """

    dynamodb = dyn_session.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)

    response = table.put_item(Item=item)

    return response

@utils.logger.catch
def batch_put_items(dyn_session, table_name, item_list, region='sa-east-1'):
    """ Put a list of items to a table """

    dynamodb = dyn_session.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)

    with table.batch_writer() as batch:
        for item in item_list:
            batch.put_item(
                Item=item
        )

@utils.logger.catch
def query_items(dyn_session, table_name, pkey, pvalue, query_type='partition',
                skey=None, svalue=None, scond='eq', region='sa-east-1'):
    """ Query items given partition key:value or/and sorting key:value """
    # pylint: disable=too-many-arguments

    dynamodb = dyn_session.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)

    if query_type == 'partition':
        pkey_obj = getattr(Key(pkey), 'eq')
        filtering_exp =  pkey_obj(pvalue)
    elif query_type == 'both':
        pkey_obj = getattr(Key(pkey), 'eq')
        skey_obj = getattr(Key(skey), scond)
        filtering_exp = pkey_obj(pvalue) & skey_obj(svalue)

    response = table.query(KeyConditionExpression=filtering_exp)

    return response['Items']
