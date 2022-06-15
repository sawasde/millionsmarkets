from utils import dynamodb

# AWS Dynamo
AWS_DYNAMO_SESSION = dynamodb.create_session()


def launch():
    print('here')
    item = dynamodb.query_items(AWS_DYNAMO_SESSION, 'mm_test', 'date', '2022_6')
    print(item)