from cmath import log

import psycopg2
from matplotlib import pyplot
from pandas import read_csv
from psycopg2.extras import DictCursor
from rpy2.robjects import pandas2ri

from science.collector.service.poloniex_public_service import PoloniexPublicService

pandas2ri.activate()

connection = psycopg2.connect("dbname=deep_crypto user=postgres password=postgres host=localhost port=5432")
cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

poloniexPublicService = PoloniexPublicService(connection, cursor)

chartData = poloniexPublicService.saveChartDataToCSV('ETH', None, None, None, '300')

dataset = read_csv('dataset.csv', index_col=['date'], parse_dates=['date'], dayfirst=True,
                   usecols=['date', 'weighted_average'])

print(dataset)
log(dataset)

dataset.plot(figsize=(12, 6))
pyplot.show()
