import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX


def modifyChartData(chartData):
    """
    Somehow modify data for learning to obtain better prediction or convenient results
    :param chartData: list of observations
    :return: the same list of observations, but modified
    """
    modifiedData = []

    # strange conversion for SARIMAX model correct input
    for o in chartData:
        modifiedData.append(np.array([o]))

    return modifiedData


def makePrediction(data: dict, futureSteps: int, hyperparameters=None) -> dict:
    """
    Make a prediction for incoming data on futureSteps
    :param data: dictionary of data where key = currencyPair and value = list of observations
    :param futureSteps: amount of steps on that algorithm will try to predict price
    :param hyperparameters: dictionary of hyperparameters for prediction model
    :return: dictionary of data where key = currencyPair and
        value = dict of predictions (equal size to futureSteps variable) where key=step_number value = prediction
    """
    if hyperparameters is None:
        hyperparameters = {'ARIMA': {'P': 1, 'D': 0, 'Q': 2, 's': 12}}

    P, D, Q = hyperparameters['ARIMA']['P'], hyperparameters['ARIMA']['D'], \
              hyperparameters['ARIMA']['Q']

    predictions = {}

    for pair, chartData in data.items():
        prediction = {}

        chartData = modifyChartData(chartData)

        for step in range(futureSteps):
            model = SARIMAX(chartData, order=(P, D, Q), enforce_stationarity=False,
                            enforce_invertibility=False)
            model_fit = model.fit(disp=0, maxiter=1000, method='nm')

            output = model_fit.forecast()
            predicted_value = output[0]
            prediction[step + 1] = predicted_value

            chartData.append(np.array([predicted_value]))

        predictions[pair] = prediction

    return predictions
