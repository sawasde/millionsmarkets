from loguru import logger

# local imports
from utils import utils, dynamodb

# AWS Dynamo
AWS_DYNAMO_SESSION = dynamodb.create_session()

# General vars
COSMOAGENT_CONFIG = {}
CHART_BASE_PATH = 'assets/'
@utils.logger.catch
def get_files():
	subprocess.run(['scp', '-r', SERVER_PATH, LOCAL_PATH])


@utils.logger.catch
def check_time(symbol):
	tms = int(utils.get_timestamp(multiplier=1))
	csv_file_path = '{}/{}.csv'.format(CHART_BASE_PATH, symbol)

	with open(csv_file_path, 'r') as f:
		last_line = f.readlines()[-1]
		last_tms = int(last_line.split(',')[0])

	diff = tms - last_tms
	print(symbol, 'LAST TMS:', utils.timestamp_to_date(last_tms), 'DIFF:', diff, 'SECONDS')

	if diff > TMS_TRESSHOLD_SEC:
		utils.logger.error('TMS NOT UPDATE CORRECTLY. DIFF {} SECONDS'.format(diff))

@utils.logger.catch
def plotter(symbol, days_ago=None):

	csv_file_path = '{}/{}.csv'.format(CHART_BASE_PATH, symbol)
	png_file_path = '{}/{}.png'.format(CHART_BASE_PATH, symbol)

	# save plot of day portion
	df = pd.read_csv(csv_file_path)
	df['zero_bound'] = 0

	if len(df) < 2:
		return

	print(symbol, 'PLOT SAVED')

	if days_ago:
		for day in days_ago:

			day_tms = utils.date_ago_timestmp(xtb_tms=False, days=int(day))
			print(symbol, day, day_tms)

			df_temp = df[df['tms'] >= day_tms]

			# AREA STUFF
			df_temp = utils.integrate_area_below(df_temp, yaxis='ptrend', dx=1)


			png_file_path_temp = png_file_path.split('.png')[0]
			png_file_path_temp += '{}.png'.format(day)


			utils.plot_sublots(	df=df_temp, 
								plot_features_dicts=[{'pclose':'g', 'pz_limit':'b', 'pd_limit': 'r'},
													#{'strend':'g', 'zero_bound':'b'},
													{'area':'r', 'zero_bound':'b'},
													#{'pz_limit':'g', 'zero_bound':'b'},
													{'mtrend':'g', 'zero_bound':'b'},
													],
								xaxis='tms', save_picture=png_file_path_temp, style='-', show=False)
			print(symbol, day, 'PLOT SAVED')

	else:
		utils.utils.plot_sublots(	df=df, 
							plot_features_dicts=[{'pclose':'g', 'pz_limit':'b'},
												{'ptrend':'g', 'zero_bound':'b'},],
							xaxis='tms', save_picture=png_file_path, style='-', show=False)

@utils.logger.catch
def remove_all_plots():

	for root, dirs, files in os.walk(CHART_BASE_PATH):
		for basename in files:
			filename = os.path.join(root, basename)
			
			if filename.endswith(f'{DAYS_AGO_TO_PLOT}.png'):
				os.remove(filename)


@logger.catch
def launch(unit_test=False):
	''' Main method '''

	# Remove previous plots
	utils.logger.info('Removing plots ...')
	remove_all_plots()

	
	for symbol in CRYPTO_MAPPER.keys():
		# Check Time
		utils.logger.info('Checking time ...')
		check_time(symbol)


		# Plot
		utils.logger.info('Saving Plots ...')
		plotter(symbol, days_ago=DAYS_AGO_TO_PLOT)


@logger.catch
def launch():
    global COSMOAGENT_CONFIG
    
    # Load config
    COSMOAGENT_CONFIG = dynamodb.get_item(AWS_DYNAMO_SESSION, 'mm_cosmoagent', {'feature' : 'prod_config'})

    # Log config
    logger.info(COSMOAGENT_CONFIG)

    launch()
    