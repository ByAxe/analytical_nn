from science.collector.service.models import sarima


class Model:
    data: dict
    futureSteps: int
    hyperparameters: dict

    def __init__(self, data: dict, futureSteps: int, hyperparameters: dict):
        """
        :param data: data based on that predictions will be made
        :param futureSteps: amount of steps in future that will be predicted
        :param hyperparameters: dictionary of hyperparameters for prediction model

        """
        self.data = data
        self.futureSteps = futureSteps
        self.hyperparameters = hyperparameters

    def predict(self) -> dict:
        """
        Choose an algorithm and make a prediction for given data
        """
        predictions = sarima.makePrediction(self.data, self.futureSteps, self.hyperparameters)
        return predictions
