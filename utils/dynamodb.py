from loguru import logger
from boto3.dynamodb.conditions import Key
import boto3
import os

@logger.catch
def create_session():
    return boto3.Session(
                            aws_access_key_id=os.getenv('AWS_ACCESS_ID'),
                            aws_secret_access_key=os.getenv('AWS_SECRET_KEY')
                        )

@logger.catch
def get_item(dyn_session, table_name, key, region='us-east-1'):

    dynamodb = dyn_session.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)

    response = table.get_item(Key=key)
    
    if 'Item' in response:
        return response['Item']['value']
    else:
        return None


@logger.catch
def put_item(dyn_session, table_name, item, region='us-east-1'):

    dynamodb = dyn_session.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)

    response = table.put_item(Item=item)

    return response

@logger.catch
def batch_put_items(dyn_session, table_name, item_list, region='us-east-1'):
    
    dynamodb = dyn_session.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)

    with table.batch_writer() as batch:
        for item in item_list:
            batch.put_item(
                Item=item
        )

@logger.catch
def query_items(dyn_session, table_name, pkey, pvalue, pcond='eq', type='partition', skey=None, svalue=None, scond='eq', region='us-east-1'):

    dynamodb = dyn_session.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)

    if type == 'partition':
        pkey_obj = getattr(Key(pkey), pcond)
        filtering_exp =  pkey_obj(pvalue)
    elif type == 'both':
        pkey_obj = getattr(Key(pkey), pcond)
        skey_obj = getattr(Key(skey), scond)
        filtering_exp = pkey_obj(pvalue) & skey_obj(svalue)

    response = table.query(KeyConditionExpression=filtering_exp)

    return response['Items']

