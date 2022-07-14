from utils import utils
import pandas as pd


@utils.logger.catch
def get_price_by_symbol(all_crypto_price, symbol='BTCBUSD'):

	for sym_dic in all_crypto_price:

		if sym_dic['symbol'] == symbol:
			return float(sym_dic['price'])

	return 0.0


@utils.logger.catch
def get_spot_balance(bin_client):
	info = bin_client.get_account()
	balances = info['balances']
	free_total = 0.0
	locked_total = 0.0

	for item in balances:
		sym = item['asset']
		free = float(item['free'])
		locked = float(item['locked'])

		print(sym, free, locked)

		free_total += free * get_price_by_symbol(sym+'BUSD')
		locked_total += locked * get_price_by_symbol(sym+'BUSD')

	return (free_total, locked_total)

@utils.logger.catch
def get_chart_data(bin_client, symbol, start='', end='', period=None, df=True, decimal=True, ohclv=True):
	''' Return Symbol Market Data as list or dataframe'''
	data = bin_client.get_historical_klines(symbol, period, start, end)

	if df:
		data = pd.DataFrame(data).astype(float)
		data.columns = ['date' , 'open', 'high', 'low', 'close', 'volume', 'ctms', 'qav', 'not', 'tbbav', 'tbqasv', 'i']

		data.date = data.date.astype(int)
		
		if not decimal:
			data = data.apply(lambda x: x * pow(10,8) if x.name in ['open', 'high', 'low', 'close'] else x)

	if ohclv:
		data = data[['date', 'open', 'close', 'high', 'low', 'volume']]		
	
	return data