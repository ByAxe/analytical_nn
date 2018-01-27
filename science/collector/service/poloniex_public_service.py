from flask import g

from science.collector.core.utils import CHART_DATA_INSERT_PLAN_SQL, \
    CURRENCIES_INSERT_PLAN_SQL, PERIODS, MAX_DATA_IN_SINGLE_QUERY, ALL
from science.collector.service.poloniex_api import Poloniex

poloniexApi = Poloniex("APIKey", "Secret".encode())


class PoloniexPublicService:

    def updateCurrencies(self):
        r = poloniexApi.returnCurrencies()

        # clear the table
        g.cur.execute("DELETE FROM poloniex.currencies")

        # prepares the query for insert
        g.cur.execute(CURRENCIES_INSERT_PLAN_SQL)

        sql = "EXECUTE currencies_insert_plan (%s, %s, %s, %s, %s, %s, %s, %s)"

        # actual insert into DB
        for symbol, info in r.items():
            g.cur.execute(sql, (info['id'], symbol, info['name'],
                                info['minConf'], info['depositAddress'], info['disabled'],
                                info['delisted'], info['frozen']))

        g.connection.commit()
        return r

    def returnMarketTradeHistory(self, currencyPair: str, start: int, end: int) -> object:
        return poloniexApi.returnMarketTradeHistory(currencyPair, start, end)

    def returnAllPairs(self):
        """
        Because keys in ticker is a currently available pairs of currencies
        :return: list of pairs
        """
        return poloniexApi.returnTicker().keys()

    def loadChartData(self, mainCurrency, secondaryCurrency, start, end, period) -> int:
        # to have actual list of currencies
        self.updateCurrencies()
        updatedElements = 0

        # If period is not specified -> go through and load the data for each one
        if period is None:
            for p in PERIODS:
                updatedElements = updatedElements + self.loadChartDataAndSplitOnParts(mainCurrency, secondaryCurrency,
                                                                                      start, end, p)
        else:
            updatedElements = self.loadChartDataAndSplitOnParts(mainCurrency, secondaryCurrency, start, end, period)
        return updatedElements

    def loadChartDataAndSplitOnParts(self, mainCurrency, secondaryCurrency, start, end, period) -> int:
        # If the range specified is bigger than allowed maximum - it must be split into affordable parts
        if ((end - start) // period) > MAX_DATA_IN_SINGLE_QUERY:
            # TODO implement!!
            pass

        return self.loadChartDataAndSpecifyTheCurrencyPair(mainCurrency, secondaryCurrency, start, end, period)

    def loadChartDataAndSpecifyTheCurrencyPair(self, mainCurrency, secondaryCurrency, start, end, period) -> int:
        def loadForBunchOfPairs(bunchPairs: list) -> int:
            """
            If there was specified ALL instead of concrete currency -> load every pair from other side
            :param bunchPairs: main and secondary list of pairs those were not specified
            :return: resulting amount of updated elements
            """
            amount = 0
            for pairs in bunchPairs:
                for pair in pairs or []:
                    m, s = pair.split("_")
                    amount = amount + len(self._loadChartDataAndSaveToDb(m, s, start, end, period))

            return amount

        mainPairs, secondaryPairs = None, None

        # If one, or both mentioned currencies == ALL -> load all actual pairs into list/s
        if mainCurrency == ALL:
            mainPairs = [p for p in self.returnAllPairs() if p.startswith(mainCurrency)]
        if secondaryCurrency == ALL:
            secondaryPairs = [p for p in self.returnAllPairs() if p.endswith(secondaryCurrency)]

        # if there were no ALL in pairs -> load everything just for specified currency pair
        if (mainPairs and secondaryPairs) is None:
            return len(self._loadChartDataAndSaveToDb(mainCurrency, secondaryCurrency, start, end, period))

        # if there was specified ALL instead of concrete currency -> load every pair from other side
        return loadForBunchOfPairs([mainPairs, secondaryPairs])

    def _loadChartDataAndSaveToDb(self, mainCurrency, secondaryCurrency, start, end, period) -> list:
        # prepares the query for insert
        g.cur.execute(CHART_DATA_INSERT_PLAN_SQL)

        sql = "EXECUTE chart_data_insert_plan (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

        # load the data from poloniex API
        currencyPair = mainCurrency + '_' + secondaryCurrency
        chartData = poloniexApi.returnChartData(currencyPair, start, end, period)

        # save the data to DB
        for o in chartData:
            g.cur.execute(sql, (mainCurrency, secondaryCurrency, period,
                                o['date'],
                                o['high'], o['low'], o['open'], o['close'],
                                o['volume'], o['quoteVolume'],
                                o['weightedAverage']))

        g.connection.commit()
        return chartData
