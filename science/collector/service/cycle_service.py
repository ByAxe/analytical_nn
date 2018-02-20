from datetime import datetime, timedelta

from science.collector.core.entities import Parameters
from science.collector.core.utils import datetimeToTimestamp
from science.collector.service.models.api.model import Model
from science.collector.service.poloniex_service import PoloniexPublicService
from science.collector.service.trader import Trader


class Cycle:
    poloniex_service: PoloniexPublicService

    def __init__(self, poloniex_service):
        """
        :param poloniex_service: wrapper for interaction with poloniex api
        """
        self.poloniex_service = poloniex_service

    def startCycleIteration(self, params_dict: dict) -> list:
        """
        Makes an iteration of a trading cycle
        :return: performed operations as dictionary
        """
        # take all the params those were passed into method and wraps in up into Object
        params = Parameters(params_dict)
        print(datetime.now(), 'Started iteration with params:', params)
        # get all the data from Poloniex
        print(datetime.now(), 'Started getting data for pairs:', params.pairs, 'And window:', params.window)
        data = self.getAllDataForParams(params.pairs, params.window, params.period, params.learn_on)

        # load data into Model and get prediction
        model = Model(data, params.steps, params.hyperparameters, params.algorithm)
        predictions = model.predict()

        # pass prediction to Trader logic and get a prepared plan
        trader = Trader(poloniex_service=self.poloniex_service, budget=params.budget, risk=params.risk,
                        steps=params.steps, pairs=params.pairs, predictions=predictions,
                        top_n=params.top_n, common_currency=params.common_currency, THRESHOLD=params.THRESHOLD,
                        current_price_buy_from=params.current_price_buy_from,
                        current_price_sell_from=params.current_price_sell_from, reopen=params.reopen)

        print(datetime.now(), 'Started plan preparation...')
        plan = trader.preparePlan()
        print(datetime.now(), 'Planned operations:', [p.__str__() for p in plan])

        # perform created plan
        if not plan:
            return ["Nothing was performed because of empty plan!"]

        operations = trader.trade(plan)
        print(datetime.now(), 'Performed operations:', [op.__str__() for op in operations])

        # return performed operations
        return operations

    def getAllDataForParams(self, pairs: list, window: dict, period: int, learn_on: str = 'weightedAverage') -> dict:
        """
        Wraps up all logic for getting data from poloniex
        :param pairs: list of pairs
        :param window: window of data on that prediction will be made
        :param period: periodicity of data
        :param learn_on: the column with price from poloniex on that to learn on our prediction algorithm
        :return: The data from poloniex for specified params
        """
        data = {}

        # parse the window to get boundaries for selection
        start, end = self.parseWindow(window)

        for pair in pairs:
            chartData = self.poloniex_service.getChartData(pair, start, end, period)

            data[pair] = [observation[learn_on] for observation in chartData]

        return data

    def parseWindow(self, window_dict=None):
        """
        Parse the window into boundaries (start, end)
        :param window_dict of data on that prediction will be made
                Example: {'WEEK':2}
        :return: two bounds for selection
        """
        if window_dict is None:
            window_dict = {'MONTH': 1}

        start, end, window, amount = None, None, None, None

        for k, v in window_dict.items():
            window = k
            amount = v

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
