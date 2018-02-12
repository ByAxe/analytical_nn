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


def makePrediction(data: dict, futureSteps: int) -> dict:
    """
    Make a prediction for incoming data on futureSteps
    :param data: dictionary of data where key = currencyPair and value = list of observations
    :param futureSteps: amount of steps on that algorithm will try to predict price
    :return: dictionary of data where key = currencyPair and value = list of predictions (equal size to futureSteps variable)
    """
    P, D, Q, step = 1, 0, 2, 12
    predictions = {}

    for pair, chartData in data.items():
        prediction = {}

        chartData = modifyChartData(chartData)

        for step in range(futureSteps):
            model = SARIMAX(chartData, seasonal_order=(P, D, Q, step), enforce_stationarity=False,
                            enforce_invertibility=False)
            model_fit = model.fit(disp=0, maxiter=1000, method='nm')

            output = model_fit.forecast()
            predicted_value = output[0]
            prediction[step + 1] = predicted_value

            chartData.append(np.array([predicted_value]))

        predictions[pair] = prediction

    return predictions
