from science.collector.service.poloniex_service import PoloniexPublicService


class Cycle:
    poloniex_service: PoloniexPublicService

    def __init__(self, poloniex_service):
        """
        TODO insert docs
        :param poloniex_service:
        """
        self.poloniex_service = poloniex_service

    def fireCycle(self, params: dict) -> dict:
        """
        TODO insert docs
        :return: performed operations and created plan
        """
        # TODO 1) takes all the params those were passed to method

        # TODO 2) get all the data from Poloniex

        # TODO 3) load data into Model and get prediction

        # TODO 4) pass prediction to Trader logic

        # TODO 5) get a response from Trader about performed operation and created plan

        return {}

    def stopCycle(self):
        """
        TODO insert docs
        """
        self.isRunning = False

    def is_running(self) -> bool:
        """
        TODO insert docs
        :return:
        """
        return self.isRunning

    class Trader:
        poloniex_service: PoloniexPublicService

        def __init__(self, poloniex_service):
            """
            TODO insert docs
            :param poloniex_service:
            """
            self.poloniex_service = poloniex_service

        def trade(self, predictions: dict) -> dict:
            """
            TODO implement following
            1. Creates a plan, based on
                A) What is currently bought
                B) Whether there are still open orders
                C) Given predictions
                D) Current situation on market (on-line sells and buys)
            2. Performs an operation if needed based on previously prepared plan
            :param predictions:
            :return:
            """
            return {}
