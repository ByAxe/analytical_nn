import math
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
        trader = self.Trader(self.poloniex_service, params.budget, params.risk, params.steps, params.pairs, predictions)
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
            chartData = self.poloniex_service.getChartData(pair, start, end, period)

            data[pair] = [observation['weightedAverage'] for observation in chartData]

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
        threshold = 0.000001

        poloniex_service: PoloniexPublicService
        budget: float
        risk: int
        steps: int
        pairs: list
        predictions: dict

        def __init__(self, poloniex_service, budget, risk, steps, pairs, predictions):
            """
            :param predictions: from model that makes predictions
            :param pairs: all pair for that prediction made
            :param steps: amount of steps in future on that prediction made
            :param risk: The number of steps that a trader will count on when building a plan,
            :param budget: allowed overall maximum (measured in USD) for all operations during the iteration
            as what exactly should happen. Measured in %.
            :param poloniex_service: wrapper for interaction with poloniex api
            """
            self.poloniex_service = poloniex_service
            self.budget = budget
            self.risk = 100 if risk > 100 else 0 if risk < 0 else risk
            self.steps = steps
            self.pairs = pairs
            self.predictions = predictions

        def preparePlan(self) -> list:
            """
            Prepares a plan, based on:
                A) What is currently bought
                B) Whether there are still open orders
                C) Given predictions
                D) Current situation on market (on-line sells and buys)
            :return: prepared plan
            """
            # get the current prices from poloniex
            ticker = self.poloniex_service.returnTickerForPairs(self.pairs)

            common_plan = {}

            # iterate through all the pairs and predicted steps and find all appropriate operations to make
            for step in range(1, self.steps + 1):
                plan_for_step = []
                for pair, prediction_list in self.predictions.items():
                    predicted_price = prediction_list[step]
                    current_price = ticker[pair]['lowerAsk']

                    delta = current_price - predicted_price
                    delta_common = self.to_common(delta, pair, ticker)

                    # If delta less than the stated threshold --> do nothing!
                    if math.fabs(delta_common) <= self.threshold:
                        continue
                    # If delta less than 0 --> we must buy currency now
                    # Example: current = 2, predicted = 4, delta = -2, so we must buy it now for 2, to sell later for 4
                    elif delta_common < 0:
                        plan_for_step.append(self.Operation('BUY', pair, delta_common))
                    # If delta more than 0 --> we must sell currency now
                    # Example: current = 4, predicted = 2, delta = 2, so we must sell it now for 4, because it'll cost only 2 afterwards
                    elif delta_common > 0:
                        plan_for_step.append(self.Operation('SELL', pair, delta_common))

                common_plan[step] = plan_for_step

            # top_n operations by profitability that must left for each step
            top_n = 3

            for step, plan in common_plan.items():
                # sort by delta (profitability metrics)
                plan.sort(key=lambda op: op.delta)

                # leave only top_n operations
                common_plan[step] = plan[:top_n]

            resulting_plan = []

            # TODO Manage the risk for the steps
            if self.steps > 1:
                # in how many steps we believe as if it must happen
                believe_in = round(self.steps * self.risk / 100)

            resulting_plan = common_plan[1]

            # TODO return resulting plan
            return resulting_plan

        def trade(self, plan: dict) -> dict:
            """
            Performs an operations if needed based on previously prepared plan
            :return: performed operations
            """
            # TODO implement
            return {}

        def to_common(self, amount, pair, ticker):
            """
            Converts amount to some common currency
            :param amount:
            :param pair: currency pair
            :param ticker: list of all pairs and its current prices
            :return: the same amount converted to common currency
            """
            return amount

        class Operation:
            op_type: str
            pair: str
            delta: float

            def __init__(self, op_type, pair, delta):
                self.op_type = op_type
                self.pair = pair
                self.delta = delta

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
