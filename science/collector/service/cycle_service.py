from datetime import datetime, timedelta

from science.collector.core.parameters import Parameters
from science.collector.core.utils import WINDOWS, datetimeToTimestamp
from science.collector.service.models.model import Model
from science.collector.service.poloniex_service import PoloniexPublicService
from science.collector.service.trader import Trader


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
        params = Parameters(params_dict)
        # get all the data from Poloniex
        data = self.getAllDataForParams(params.pairs, params.window, params.period)

        # load data into Model and get prediction
        model = Model(data, params.steps)
        predictions = model.predict()

        # pass prediction to Trader logic and get a prepared plan
        trader = Trader(self.poloniex_service, params.budget, params.risk, params.steps, params.pairs, predictions)
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
