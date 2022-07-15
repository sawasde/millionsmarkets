from utils import dynamodb, utils
import pandas as pd
import json
from decimal import Decimal

CRYPTO_MAPPER = ['ETHBUSD', 'ADABUSD', 'SOLBUSD', 'DOTBUSD', 'BNBBUSD','AXSBUSD']
TEST = False
# AWS Dynamo
AWS_DYNAMO_SESSION = dynamodb.create_session()

def launch():

    for crypto in CRYPTO_MAPPER:

        print('migrating', crypto)

        df = pd.read_csv('cosmobot/historical_assets/BTCBUSD.csv')
        #tms,ptrend,mtrend,strend,pclose,pd_limit,pz_limit
        item_list = []
        for i, row in df.iterrows():
            to_put = {}
            timestamp = int(row['tms'])
            date = utils.timestamp_to_date(timestamp)
            week = date.isocalendar()[1]
            year = date.isocalendar()[0]
            iweek = f'{year}_{week}'
            to_put = {  'week' : iweek, 
                        'timestamp' : timestamp,
                        'ptrend' : row['ptrend'],
                        'mtrend' : row['mtrend'],
                        'strend' : row['strend'],
                        'pclose' : row['pclose'],
                        'pd_limit' : row['pd_limit'],
                        'pz_limit' : row['pz_limit'] }

            if year != 2022 or week < 24:
                continue

            else:

                print(f'Progress {i*100/len(df)} %', end='\r')
                item = json.loads(json.dumps(to_put), parse_float=Decimal)

                item_list.append(item)

            # BTC B USD 
        table_symbol = crypto[:3] + crypto[4:] + 'T'

        if TEST:
            #if year != 2022 or week <= 17:
            #    continue
            dynamodb.put_item(AWS_DYNAMO_SESSION, f'cosmobot_historical_{table_symbol}_test', item_list[0])
            break
        else:
            print(len(item_list))
            dynamodb.batch_put_items(AWS_DYNAMO_SESSION, f'mm_cosmobot_historical_{table_symbol}', item_list)
            #dynamodb.put_item(AWS_DYNAMO_SESSION, f'mm_cosmobot_historical_{table_symbol}', item)


if __name__ == '__main__':
    ''' cli '''
    print('ok')


