from datetime import datetime, timedelta

from science.collector.core.utils import WINDOWS, datetimeToTimestamp
from science.collector.service.models.model import Model
from science.collector.service.poloniex_service import PoloniexPublicService


class Cycle:
    poloniex_service: PoloniexPublicService

    def __init__(self, poloniex_service):
        """
        :param poloniex_service: wrapper for interaction with poloniex api
        """
        self.poloniex_service = poloniex_service

    def startCycleIteration(self, params_dict: dict) -> dict:
        """
        Makes an iteration of a trading cycle
        :return: performed operations as dictionary
        """
        # take all the params those were passed into method and wraps in up into Object
        params = self.Parameters(params_dict)
        # get all the data from Poloniex
        data = self.getAllDataForParams(params.pairs, params.window, params.period)

        # load data into Model and get prediction
        model = Model(data, params.steps)
        predictions = model.predict()

        # pass prediction to Trader logic and get a prepared plan
        trader = self.Trader(self.poloniex_service, params.budget, params.risk, predictions)
        plan = trader.preparePlan()

        # perform created plan
        operations = trader.trade(plan)

        # return performed operations
        return operations

    def getAllDataForParams(self, pairs: list, window: dict, period: int) -> dict:
        """
        Wraps up all logic for getting data from poloniex
        :param pairs: list of pairs
        :param window: window of data on that prediction will be made
        :param period: periodicity of data
        :return: The data from poloniex for specified params
        """
        data = {}

        # parse the window to get boundaries for selection
        start, end = self.parseWindow(window)

        for pair in pairs:
            mainCurrency, secondaryCurrency = pair.split('_')
            chartData = self.poloniex_service.getChartData(mainCurrency, secondaryCurrency, start, end, period,
                                                           fields=['weighted_average'])
            data[pair] = chartData

        return data

    def parseWindow(self, window_dict: dict):
        """
        Parse the window into boundaries (start, end)
        :param window_dict of data on that prediction will be made
                Example: {'WEEK':2}
        :return: two bounds for selection
        """
        start, end, window, amount = None, None, None, None
        defaultWindow, defaultAmount = 'MONTH', 1

        for k, v in window_dict.items():
            window = k
            amount = v

        if window not in WINDOWS:
            print('Window was not in allowed values so it will be counted for default: ',
                  defaultWindow, defaultAmount)

            window = defaultWindow

        end = datetime.now()

        if 'HOUR' == window:
            start = end - timedelta(hours=amount)
        elif 'DAY' == window:
            start = end - timedelta(days=amount)
        elif 'WEEK' == window:
            start = end - timedelta(weeks=amount)
        elif 'MONTH' == window:
            start = end - timedelta(weeks=amount * 4)

        return [datetimeToTimestamp(start), datetimeToTimestamp(end)]

    class Trader:
        poloniex_service: PoloniexPublicService
        budget: float
        risk: int
        predictions: dict

        def __init__(self, poloniex_service, budget, risk, predictions):
            """
            :param predictions: from model that makes predictions
            :param budget: allowed overall maximum (measured in USD) for all operations during the iteration
            :param risk: The number of steps that a trader will count on when building a plan,
            as what exactly should happen. Measured in %.
            :param poloniex_service: wrapper for interaction with poloniex api
            """
            self.poloniex_service = poloniex_service
            self.budget = budget
            self.risk = risk
            self.predictions = predictions

        def preparePlan(self) -> dict:
            """
            Prepares a plan, based on:
                A) What is currently bought
                B) Whether there are still open orders
                C) Given predictions
                D) Current situation on market (on-line sells and buys)
            :return: prepared plan
            """
            # TODO implement
            return {}

        def trade(self, plan: dict) -> dict:
            """
            Performs an operations if needed based on previously prepared plan
            :return: performed operations
            """
            # TODO implement
            return {}

    class Parameters:
        budget: float
        pairs: list
        risk: int
        window: dict
        period: int
        steps: int

        def __init__(self, params):
            """
            - Budget: allowed overall maximum (measured in USD) for all operations during the iteration
            - Pairs: the list of pairs among those algorithm creates a plan
            - Risk: The number of steps that a trader will count on when building a plan,
                as what exactly should happen. Measured in %.
                Risk = 100% means that algorithm will count on farthest predicted step,
                    as if it must happen.
                Risk = 0% means that algorithm only counts on the closest predicted step
            - Window: window of data on that prediction will be made
                Example: {'WEEK':2}
            - Period: periodicity of predicted data
            - Steps: amount of steps in future (periods) on that prediction will be made
            :param params: parameters as dictionary
            """
            self.budget = params['budget']
            self.pairs = params['pairs']
            self.risk = params['risk']
            self.window = params['window']
            self.period = params['period']
            self.steps = params['steps']
