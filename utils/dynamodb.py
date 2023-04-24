from utils import utils
from boto3.dynamodb.conditions import Key
import boto3
import os

@utils.logger.catch
def load_feature_value_config(dyn_session, table, debug=True):
    utils.logger.info(f'Load Config dict for {table}')
   
    if debug:
        return get_item(dyn_session, table, {'feature' : 'test_config'})
    else:
        return get_item(dyn_session, table, {'feature' : 'prod_config'})


@utils.logger.catch
def create_session(from_lambda=False):
    if from_lambda:
        return boto3.Session()
    else:
        return boto3.Session(
                            aws_access_key_id=os.getenv('AWS_ACCESS_ID'),
                            aws_secret_access_key=os.getenv('AWS_SECRET_KEY')
                            )

@utils.logger.catch
def get_item(dyn_session, table_name, key, region='sa-east-1'):

    dynamodb = dyn_session.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)

    response = table.get_item(Key=key)
    
    if 'Item' in response:
        return response['Item']['value']
    else:
        return None


@utils.logger.catch
def put_item(dyn_session, table_name, item, region='sa-east-1'):

    dynamodb = dyn_session.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)

    response = table.put_item(Item=item)

    return response

@utils.logger.catch
def batch_put_items(dyn_session, table_name, item_list, region='sa-east-1'):
    
    dynamodb = dyn_session.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)

    with table.batch_writer() as batch:
        for item in item_list:
            batch.put_item(
                Item=item
        )

@utils.logger.catch
def query_items(dyn_session, table_name, pkey, pvalue, type='partition', skey=None, svalue=None, scond='eq', region='sa-east-1'):

    dynamodb = dyn_session.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)

    if type == 'partition':
        pkey_obj = getattr(Key(pkey), 'eq')
        filtering_exp =  pkey_obj(pvalue)
    elif type == 'both':
        pkey_obj = getattr(Key(pkey), 'eq')
        skey_obj = getattr(Key(skey), scond)
        filtering_exp = pkey_obj(pvalue) & skey_obj(svalue)

    response = table.query(KeyConditionExpression=filtering_exp)

    return response['Items']

