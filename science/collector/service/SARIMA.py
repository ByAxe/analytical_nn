from cmath import log

import psycopg2
from pandas import read_csv
from psycopg2.extras import DictCursor
from rpy2.robjects import pandas2ri
from rpy2.robjects.packages import importr

from science.collector.service.poloniex_public_service import PoloniexPublicService

pandas2ri.activate()

connection = psycopg2.connect("dbname=deep_crypto user=postgres password=postgres host=localhost port=5432")
cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

poloniexPublicService = PoloniexPublicService(connection, cursor)

poloniexPublicService.saveChartDataToCSV(main_currency='BTC', secondary_currency='ETH', start='1483218000',
                                         end='1514754000', period='300')

dataset = read_csv('dataset.csv', index_col=['date'], parse_dates=['date'], dayfirst=True,
                   usecols=['date', 'weighted_average'])

dataset['weighted_average'] = dataset['weighted_average'].apply(lambda w: log(w))

stats = importr('stats')
tseries = importr('tseries')

r_df = pandas2ri.py2ri(dataset)
y = stats.ts(r_df)

ad = tseries.adf_test(y, alternative="stationary", k=52)

diff1lev = dataset.diff(periods=1).dropna()
diff1lev_season = diff1lev.diff(52).dropna()
diff1lev.plot(figsize=(12, 6))
# print('p.value: %f' % sm.tsa.adfuller(diff1lev, maxlag=52)[1])

# dataset.plot(figsize=(12, 6))
# pyplot.show()
