from loguru import logger
import boto3
import os

@logger.catch
def create_session():
    return boto3.Session(
                            aws_access_key_id=os.getenv('AWS_ACCESS_ID'),
                            aws_secret_access_key=os.getenv('AWS_SECRET_KEY')
                        )

@logger.catch
def get_item(dyn_session, table_name, feature):
    dynamodb = dyn_session.resource('dynamodb', region_name="us-east-1")
    table = dynamodb.Table(table_name)

    response = table.get_item(
        Key={
            'feature': feature,

        }
    )
    
    if 'Item' in response:
        return response['Item']['value']
    else:
        return None


@logger.catch
def put_item(dyn_session, table_name, feature, value):
    dynamodb = dyn_session.resource('dynamodb', region_name="us-east-1")
    table = dynamodb.Table(table_name)

    item = {
            'feature': feature,
            'value' : value
        }

    response = table.put_item(Item=item)

    return response
    


