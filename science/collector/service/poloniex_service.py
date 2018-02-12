import time
from datetime import datetime

from science.collector.core.utils import CHART_DATA_INSERT_PLAN_SQL, \
    CURRENCIES_INSERT_PLAN_SQL, PERIODS, ALL, MAX_DATA_IN_SINGLE_QUERY
from science.collector.service.poloniex_api import Poloniex

poloniexApi = Poloniex("APIKey", "Secret".encode())


class PoloniexPublicService:
    connection = None
    cursor = None

    def __init__(self, connection, cursor):
        self.connection = connection
        self.cursor = cursor

        # prepares the query for insert
        self.cursor.execute(CURRENCIES_INSERT_PLAN_SQL)

        # prepares the query for insert
        self.cursor.execute(CHART_DATA_INSERT_PLAN_SQL)

        self.connection.commit()

    def updateCurrencies(self):
        r = poloniexApi.returnCurrencies()

        # clear the table
        self.cursor.execute("DELETE FROM poloniex.currencies")

        sql = "EXECUTE currencies_insert_plan (%s, %s, %s, %s, %s, %s, %s, %s)"

        # actual insert into DB
        for symbol, info in r.items():
            self.cursor.execute(sql, (info['id'], symbol, info['name'],
                                      info['minConf'], info['depositAddress'], info['disabled'],
                                      info['delisted'], info['frozen']))

        self.connection.commit()
        return r

    def returnMarketTradeHistory(self, currencyPair: str, start: int, end: int) -> object:
        return poloniexApi.returnMarketTradeHistory(currencyPair, start, end)

    def deleteChartData(self, mainCurrency, secondaryCurrency, start, end, period):
        """
        Removes all the elements those are fit for parameters
        If some are not mentioned ==> remove all within current parameter.
        Example: period is None ==> remove data with all periods
        :param mainCurrency: main currency of the pair
        :param secondaryCurrency: second currency of the pair
        :param start: start of period
        :param end: end of period
        :param period: periodicity of data
        """
        sql = "DELETE FROM poloniex.chart_data WHERE"
        sql += " period = " + period if period is not None else ""
        sql += " date >= " + start if start is not None else ""
        sql += " date <= " + end if end is not None else ""
        sql += " main_currency = \'" + mainCurrency + "\'" if mainCurrency is not None else ""
        sql += " secondary_currency = \'" + secondaryCurrency + "\'" if secondaryCurrency is not None else ""

        sql = sql[:-5] if sql.endswith("WHERE") else sql

        self.cursor.execute(sql)
        self.connection.commit()

    def loadChartData(self, mainCurrency, secondaryCurrency, start, end, period) -> int:
        """
        Loads all the elements within mentioned parameters into DB
        Wrapper method
        :param mainCurrency: main currency of the pair
        :param secondaryCurrency: second currency of the pair
        :param start: start of period
        :param end: end of period
        :param period: periodicity of data
        :return: amount of elements those were loaded
        """
        # to have actual list of currencies
        self.updateCurrencies()
        i = 0

        periods = self.specifyPeriod(period)
        mainPairs, secondaryPairs = self.specifyPairs(mainCurrency, secondaryCurrency)

        for p in periods:
            if mainPairs is None and secondaryPairs is None:
                i += self._loadChartDataAndSaveToDb(mainCurrency, secondaryCurrency, start, end, p)
            else:
                for pair in mainPairs or []:
                    m, s = pair.split('_')
                    i += self._loadChartDataAndSaveToDb(m, s, start, end, p)
                for pair in secondaryPairs or []:
                    m, s = pair.split('_')
                    i += self._loadChartDataAndSaveToDb(m, s, start, end, p)
        return i

    def specifyPeriod(self, period) -> list:
        return PERIODS if period is None else [period]

    def specifyPairs(self, m, s) -> list:
        """
        If there was specified ALL instead of concrete currency -> load every pair from other side

        :param m: main currency of pair
        :param s: secondary currency of pair
        :return: list of lists of currency pairs
        """
        mainPairs, secondaryPairs = None, None

        if m == ALL and s == ALL:
            mainPairs = self.returnAllPairs()
        elif m == ALL:
            mainPairs = [p for p in self.returnAllPairs() if p.endswith(s)]
        elif s == ALL:
            secondaryPairs = [p for p in self.returnAllPairs() if p.startswith(m)]

        return [mainPairs, secondaryPairs]

    def returnAllPairs(self):
        """
        Because keys in ticker is a currently available pairs of currencies
        :return: list of pairs
        """
        return poloniexApi.returnTicker().keys()

    def loadChartDataAndSplitOnParts(self, mainCurrency, secondaryCurrency, start, end, period) -> int:
        """
        Splits the selections on affordable parts and loads into DB
        Wrapper method
        :param mainCurrency: main currency of the pair
        :param secondaryCurrency: second currency of the pair
        :param start: start of period
        :param end: end of period
        :param period: periodicity of data
        :return: amount of elements those were loaded
        """
        updatedElements = 0
        # If the range specified is bigger than allowed maximum - it must be split into affordable parts
        if ((end - start) // period) > MAX_DATA_IN_SINGLE_QUERY:
            tempEnd = start
            while tempEnd <= end:
                print(int(time.time()), ' Updated Elements: ', updatedElements)
                tempEnd += period * MAX_DATA_IN_SINGLE_QUERY
                updatedElements += self._loadChartDataAndSaveToDb(mainCurrency, secondaryCurrency, start,
                                                                  end if tempEnd > end else tempEnd,
                                                                  period)
        else:
            updatedElements = self._loadChartDataAndSaveToDb(mainCurrency, secondaryCurrency, start, end, period)
        return updatedElements

    def _loadChartDataAndSaveToDb(self, mainCurrency, secondaryCurrency, start, end, period) -> int:
        # time.sleep(PAUSE_BETWEEN_QUERIES_SECONDS)
        print(int(time.time()), ': ', mainCurrency, secondaryCurrency, start, end, period, end='\n\n')

        sql = "EXECUTE chart_data_insert_plan (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

        # load the data from poloniex API
        currencyPair = mainCurrency + '_' + secondaryCurrency
        chartData = poloniexApi.returnChartData(currencyPair, start, end, period)

        if not chartData or len(chartData) < 2:
            return len([])

        print(len(chartData))
        # save the data to DB
        for o in chartData:
            self.cursor.execute(sql, (mainCurrency, secondaryCurrency, period,
                                      o['date'],
                                      o['high'], o['low'], o['open'], o['close'],
                                      o['volume'], o['quoteVolume'],
                                      o['weightedAverage']))

        self.connection.commit()
        return len(chartData)

    def getChartData(self, mainCurrency, secondaryCurrency, start, end, period, fields: list = None,
                     limit='1000') -> list:
        sql = "SELECT "

        sql += ', '.join(fields) if fields is not None else "*"
        sql += " FROM poloniex.chart_data WHERE"

        sql += " period = " + str(period) + " AND" if str(period) is not None else ""
        sql += " date >= " + str(start) + " AND" if str(start) is not None else ""
        sql += " date <= " + str(end) + " AND" if str(end) is not None else ""
        sql += " main_currency = '" + mainCurrency + "'" + " AND" if mainCurrency is not None else ""
        sql += " secondary_currency = '" + secondaryCurrency + "'" + " AND" if secondaryCurrency is not None else ""

        sql = sql[:-4] if sql.endswith(" AND") else sql
        sql = sql[:-5] if sql.endswith("WHERE") else sql
        sql += " LIMIT " + limit if limit is not None else ""

        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def saveChartDataToCSV(self, main_currency, secondary_currency, start, end, period, file_name='dataset'):
        import pandas as pd

        chartData = self.getChartData(main_currency, secondary_currency, start, end, period, limit=None)

        columns = ['main_currency', 'secondary_currency', 'date', 'period', 'high', 'low',
                   'open', 'close', 'volume', 'quote_volume', 'weighted_average']

        df = pd.DataFrame([i.copy() for i in chartData], columns=columns)

        df['date'] = df['date'].apply(lambda d: datetime.fromtimestamp(d).strftime('%Y-%m-%d %H:%M:%S'))

        df.to_csv(file_name + '.csv')
