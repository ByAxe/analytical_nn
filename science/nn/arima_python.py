import calendar
import warnings
from datetime import date
from math import sqrt

import psycopg2
from pandas import read_csv
from psycopg2.extras import DictCursor
from sklearn.metrics import mean_squared_error
from statsmodels.tsa.statespace.sarimax import SARIMAX

from science.collector.service.poloniex_public_service import PoloniexPublicService

warnings.filterwarnings('ignore')


def prepare_csv(week_range, month_range):
    connection = psycopg2.connect("dbname=deep_crypto user=postgres password=postgres host=localhost port=5432")
    cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

    poloniexPublicService = PoloniexPublicService(connection, cursor)

    poloniexPublicService.saveChartDataToCSV(file_name='week_data', main_currency='BTC', secondary_currency='ETH',
                                             start=week_range['start'],
                                             end=week_range['end'], period='300')

    poloniexPublicService.saveChartDataToCSV(file_name='month_data', main_currency='BTC', secondary_currency='ETH',
                                             start=month_range['start'],
                                             end=month_range['end'], period='300')


def split_data(series, percentage):
    X = series.values
    size = int(len(X) * percentage)
    train, test = X[0:size], X[size:len(X)]
    history = [x for x in train]
    return [history, test]


def evaluate_model(params, train, test, print_period=10):
    [P, D, Q, s] = params

    predictions = list()

    for t in range(len(test)):
        model = SARIMAX(train, seasonal_order=(P, D, Q, s), enforce_stationarity=False)
        model_fit = model.fit(disp=0, maxiter=1000, method='nm')

        output = model_fit.forecast()
        yhat = output[0]
        predictions.append(yhat)

        obs = test[t]
        train.append(obs)

        if (t % print_period) == 0:
            print('predicted=%f, expected=%f' % (yhat, obs))

    error = mean_squared_error(test, predictions)
    rmse = sqrt(error)
    return rmse


def prepare_params():
    P_list = range(5)
    D_list = range(5)
    Q_list = range(5)
    s_list = [0, 1, 2, 4, 6, 12, 24, 48, 60, 144, 288, 576]

    return [P_list, D_list, Q_list, s_list]


def prepare_data():
    week_data = read_csv('week_data.csv', index_col=['date'], parse_dates=['date'], dayfirst=True,
                         usecols=['date', 'weighted_average'])

    [week_train, week_test] = split_data(week_data, 0.98)

    month_data = read_csv('month_data.csv', index_col=['date'], parse_dates=['date'], dayfirst=True,
                          usecols=['date', 'weighted_average'])

    [month_train, month_test] = split_data(month_data, 0.99)

    return [week_train, week_test, month_train, month_test]


def choose_the_best_params():
    best = {'P': 0, 'D': 0, 'Q': 0, 's': 0, 'RMSE': 100000}

    [P_list, D_list, Q_list, s_list] = prepare_params()
    [week_train, week_test, month_train, month_test] = prepare_data()

    iteration = 0

    for s in s_list:
        for P in P_list:
            for D in D_list:
                for Q in Q_list:
                    # Week evaluation
                    week_rmse = evaluate_model([P, D, Q, s], train=week_train, test=week_test, print_period=50)

                    # Month evaluation
                    month_rmse = evaluate_model([P, D, Q, s], train=month_train, test=month_test,
                                                print_period=100)

                    # Average RMSE
                    RMSE_NEW = (week_rmse + month_rmse) / 2

                    # Choosing the best parameters
                    if best['RMSE'] > RMSE_NEW:
                        best['P'], best['D'], best['Q'], best['s'], best['RMSE'], = P, D, Q, s, RMSE_NEW

                    # print something
                    iteration += 1
                    print('\nIteration number =', iteration)
                    print('\tBest for now: ', best)

    return best


def main():
    week_start = str(calendar.timegm(date(year=2018, month=1, day=1).timetuple()))
    week_end = str(calendar.timegm(date(year=2018, month=1, day=8).timetuple()))

    month_start = str(calendar.timegm(date(year=2017, month=12, day=1).timetuple()))
    month_end = str(calendar.timegm(date(year=2018, month=1, day=1).timetuple()))

    week_range = {'start': week_start, 'end': week_end}
    month_range = {'start': month_start, 'end': month_end}

    prepare_csv(month_range, week_range)

    params_dict = choose_the_best_params()
    print(params_dict)


if __name__ == '__main__':
    main()
