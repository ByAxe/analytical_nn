import calendar
import multiprocessing
import warnings
from datetime import date
from math import sqrt
from multiprocessing import Process
from operator import itemgetter

import psycopg2
from pandas import read_csv
from psycopg2.extras import DictCursor
from sklearn.metrics import mean_squared_error
from statsmodels.tsa.statespace.sarimax import SARIMAX

from science.collector.service.poloniex_service import PoloniexPublicService

warnings.filterwarnings('ignore')

trials = []


def prepare_csv(some_range):
    connection = psycopg2.connect("dbname=deep_crypto user=postgres password=postgres host=localhost port=5432")
    cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

    poloniexPublicService = PoloniexPublicService(connection, cursor)

    poloniexPublicService.saveChartDataToCSV(main_currency='BTC', secondary_currency='ETH',
                                             start=some_range['start'],
                                             end=some_range['end'], period='300')


def split_data(series, percentage):
    X = series.values
    size = int(len(X) * percentage)
    train, test = X[0:size], X[size:len(X)]
    history = [x for x in train]
    return [history, test]


def evaluate_model(params, train, test, print_period=50):
    global trials

    # print('Starting evaluation of model with params:', params)
    [P, D, Q, s] = params

    predictions = list()

    for t in range(len(test)):
        model = SARIMAX(train, seasonal_order=(P, D, Q, s), enforce_stationarity=False, enforce_invertibility=False)
        model_fit = model.fit(disp=0, maxiter=1000, method='nm')

        output = model_fit.forecast()
        yhat = output[0]
        predictions.append(yhat)

        obs = test[t]
        train.append(obs)

        if (t % print_period) == 0:
            print('Params:', params, 'predicted=%f, expected=%f' % (yhat, obs))
            pass

    error = mean_squared_error(test, predictions)
    rmse = sqrt(error)

    dit = {'P': P, 'D': D, 'Q': Q, 's': s, 'RMSE': rmse}
    print(dit)


def prepare_params():
    P_list = [1]
    D_list = [0]
    Q_list = [2]
    s_list = [12]

    return [P_list, D_list, Q_list, s_list]


def prepare_data():
    data = read_csv('dataset.csv', index_col=['date'], parse_dates=['date'], dayfirst=True,
                    usecols=['date', 'weighted_average'])

    [train, test] = split_data(data, 0.995)

    return [train, test]


def choose_the_best_params():
    [P_list, D_list, Q_list, s_list] = prepare_params()
    [train, test] = prepare_data()

    # processes = []

    for s in s_list:
        processes = []
        for P in P_list:
            for D in D_list:
                processes = []
                for Q in Q_list:
                    try:
                        new_process = multiprocessing.Process(target=evaluate_model,
                                                              args=[[P, D, Q, s], train, test, 10])
                        new_process.start()
                        processes.append(new_process)
                    except BaseException:
                        print('Exception Occurred!')
        for p in processes:
            p.join()


def main():
    day_start = str(calendar.timegm(date(year=2018, month=1, day=7).timetuple()))
    day_end = str(calendar.timegm(date(year=2018, month=1, day=8).timetuple()))

    week_start = str(calendar.timegm(date(year=2018, month=1, day=1).timetuple()))
    week_end = str(calendar.timegm(date(year=2018, month=1, day=8).timetuple()))

    month_start = str(calendar.timegm(date(year=2017, month=12, day=15).timetuple()))
    month_end = str(calendar.timegm(date(year=2018, month=1, day=15).timetuple()))

    day_range = {'start': day_start, 'end': day_end}
    week_range = {'start': week_start, 'end': week_end}
    month_range = {'start': month_start, 'end': month_end}

    prepare_csv(month_range)
    choose_the_best_params()
    top = sorted(trials, key=itemgetter('RMSE'), reverse=True)[:3]

    for r in top:
        print(r)

    # print(params_dict)


if __name__ == '__main__':
    main()
