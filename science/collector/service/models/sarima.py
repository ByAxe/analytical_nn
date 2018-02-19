import multiprocessing
import warnings
from datetime import datetime

import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.simplefilter(action='ignore', category=FutureWarning)


def makePrediction(data: dict, futureSteps: int, hyperparameters=None) -> dict:
    """
    Make a prediction for incoming data on futureSteps
    :param data: dictionary of data where key = currencyPair and value = list of observations
    :param futureSteps: amount of steps on that algorithm will try to predict price
    :param hyperparameters: dictionary of hyperparameters for prediction model
    :return: dictionary of data where key = currencyPair and
        value = dict of predictions (equal size to futureSteps variable) where key=step_number value = prediction
    """
    pool_size = multiprocessing.cpu_count() - 1
    pool = multiprocessing.Pool(
        processes=pool_size,
        maxtasksperchild=2,
    )

    if hyperparameters is None:
        hyperparameters = {'SARIMA': {'P': 1, 'D': 0, 'Q': 2, 's': 12}}

    inputs = [
        (pair, chartData, futureSteps, hyperparameters)
        for pair, chartData in data.items()
    ]

    predictions = pool.map(makePredictionForPair, inputs)

    pool.close()  # no more tasks
    pool.join()  # wrap up current tasks

    return predictions


def makePredictionForPair(parameters: tuple) -> dict:
    pair, chartData, futureSteps, hyperparameters = parameters

    print(datetime.now(), 'Started prediction for pair:', pair)

    P, D, Q, s = hyperparameters['SARIMA']['P'], hyperparameters['SARIMA']['D'], \
                 hyperparameters['SARIMA']['Q'], hyperparameters['SARIMA']['s']

    prediction = {}

    chartData = modifyChartData(chartData)

    for step in range(futureSteps):
        model = SARIMAX(chartData, seasonal_order=(P, D, Q, s), enforce_stationarity=False,
                        enforce_invertibility=False)
        model_fit = model.fit(disp=0, maxiter=1500, method='nm')

        output = model_fit.forecast()
        predicted_value = output[0]
        prediction[step + 1] = predicted_value

        chartData.append(np.array([predicted_value]))

    print(datetime.now(), 'Finished prediction for pair:', pair)
    return prediction


def modifyChartData(chartData: list) -> list:
    """
    Somehow modify data for learning to obtain better prediction or convenient results
    :param chartData: list of observations
    :return: the same list of observations, but modified
    """
    modifiedData = []

    # strange conversion for SARIMAX model correct input
    for o in chartData:
        modifiedData.append(np.array([float(o)]))

    return modifiedData
