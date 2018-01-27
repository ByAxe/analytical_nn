from flask import g

from science.collector.core.utils import MAX_DATA_IN_SINGLE_QUERY, CHART_DATA_INSERT_PLAN_SQL, \
    CURRENCIES_INSERT_PLAN_SQL
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

    def actualizePairs(self, mainCurrency: str, secondaryCurrency: str, start: int, end: int, period: int) -> list:
        self.updateCurrencies()

        # prepares the query for insert
        g.cur.execute(CHART_DATA_INSERT_PLAN_SQL)

        sql = "EXECUTE chart_data_insert_plan (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

        # If the range specified is bigger than allowed maximum - it must be split into affordable parts
        if ((end - start) // period) > MAX_DATA_IN_SINGLE_QUERY:
            # TODO implement!!
            pass

        currencyPair = mainCurrency + '_' + secondaryCurrency
        chartData = poloniexApi.returnChartData(currencyPair, start, end, period)

        for o in chartData:
            g.cur.execute(sql, (mainCurrency, secondaryCurrency, period,
                                o['date'],
                                o['high'], o['low'], o['open'], o['close'],
                                o['volume'], o['quoteVolume'],
                                o['weightedAverage']))

        g.connection.commit()
        return chartData
