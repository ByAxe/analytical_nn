from science.collector.service.models import sarima


class Model:
    data: dict
    futureSteps: int

    def __init__(self, data: dict, futureSteps):
        """
        :param data: data based on that predictions will be made
        :param futureSteps: amount of steps in future that will be predicted
        """
        self.data = data
        self.futureSteps = futureSteps

    def predict(self) -> dict:
        """
        Choose an algorithm and make a prediction for given data
        """
        predictions = sarima.makePrediction(self.data, self.futureSteps)
        return predictions
