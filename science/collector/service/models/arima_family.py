import multiprocessing
import numpy as np
import warnings
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.simplefilter(action='ignore', category=FutureWarning)


def makePrediction(data: dict, futureSteps: int, hyperparameters=None, algorithm='ARIMA') -> dict:
    """
    Make a prediction for incoming data on futureSteps
    :param algorithm: provided algorithm for calculation of prediction
    :param data: dictionary of data where key = currencyPair and value = list of observations
    :param futureSteps: amount of steps on that algorithm will try to predict price
    :param hyperparameters: dictionary of hyperparameters for prediction model
    :return: dictionary of data where key = currencyPair and
        value = dict of predictions (equal size to futureSteps variable) where key=step_number value = prediction
    """

    # Create pool and specify amount of simultaneous processes
    pool_size = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(
        processes=pool_size
    )

    # if hyperparameters are not specified -> do it default params
    if hyperparameters is None:
        if algorithm == 'ARIMA':
            hyperparameters = {'SARIMA': {'P': 1, 'D': 0, 'Q': 2, 's': 12}}
        elif algorithm == 'SARIMA':
            hyperparameters = {'SARIMA': {'P': 1, 'D': 0, 'Q': 2}}

    # create list of inputs for the function that will be run in parallel
    inputs = [
        (pair, chartData, futureSteps, hyperparameters, algorithm)
        for pair, chartData in data.items()
    ]

    # pass all the inputs into functions and get predictions from them
    predictions = pool.map(makePredictionForPair, inputs)

    pool.close()  # no more tasks
    pool.join()  # wrap up current tasks

    return predictions


def makePredictionForPair(parameters: tuple) -> dict:
    pair, chartData, futureSteps, hyperparameters, algorithm = parameters

    P, D, Q = hyperparameters[algorithm]['P'], hyperparameters[algorithm]['D'], \
              hyperparameters[algorithm]['Q']

    if algorithm == 'SARIMA':
        s = hyperparameters['SARIMA']['s']

    prediction = {}

    chartData = modifyChartData(chartData)

    for step in range(futureSteps):
        if algorithm == 'ARIMA':
            model = SARIMAX(chartData, order=(P, D, Q), enforce_stationarity=False,
                            enforce_invertibility=False)
        elif algorithm == 'SARIMA':
            model = SARIMAX(chartData, seasonal_order=(P, D, Q, s), enforce_stationarity=False,
                            enforce_invertibility=False)
        model_fit = model.fit(disp=0, maxiter=2500, method='nm')

        output = model_fit.forecast()
        predicted_value = output[0]
        prediction[step + 1] = predicted_value

        chartData.append(np.array([predicted_value]))

    return {pair: prediction}


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
