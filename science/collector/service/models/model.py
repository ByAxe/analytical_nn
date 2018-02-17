from datetime import datetime

from science.collector.service.models import sarima


class Model:
    data: dict
    futureSteps: int
    hyperparameters: dict
    algorithm: str

    def __init__(self, data: dict, futureSteps: int, hyperparameters: dict, algorithm: str):
        """
        :param data: data based on that predictions will be made
        :param futureSteps: amount of steps in future that will be predicted
        :param hyperparameters: dictionary of hyperparameters for prediction model
        :param algorithm: what algorithm to use for prediction
        """
        self.data = data
        self.futureSteps = futureSteps
        self.hyperparameters = hyperparameters
        self.algorithm = algorithm

    def predict(self) -> dict:
        """
        Choose an algorithm and make a prediction for given data
        """
        predictions = None

        print(datetime.now(), 'Prediction algorithm started...')

        if self.algorithm == "SARIMA":
            predictions = sarima.makePrediction(self.data, self.futureSteps, self.hyperparameters)
        if self.algorithm == "ARIMA":
            predictions = sarima.makePrediction(self.data, self.futureSteps, self.hyperparameters)

        print(datetime.now(), 'Prediction algorithm finished')

        return predictions
