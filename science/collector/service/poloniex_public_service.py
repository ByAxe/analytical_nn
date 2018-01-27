from flask import g

from science.collector.core.utils import MAX_DATA_IN_SINGLE_QUERY
from science.collector.service.poloniex_api import Poloniex

poloniexApi = Poloniex("APIKey", "Secret".encode())


class PoloniexPublicService:

    def updateCurrencies(self):
        r = poloniexApi.returnCurrencies()

        # clear the table
        g.cur.execute("DELETE FROM poloniex.currencies")

        # prepares the query for insert
        g.cur.execute("PREPARE currencies_insert_plan AS " +
                      "INSERT INTO poloniex.currencies "
                      "(id, symbol, name, min_conf, deposit_address, disabled, delisted, frozen) "
                      "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)")

        sql = "EXECUTE currencies_insert_plan (%s, %s, %s, %s, %s, %s, %s, %s)"

        # actual insert into DB
        for symbol, info in r.items():
            g.cur.execute(sql, (info['id'], symbol, info['name'],
                                info['minConf'], info['depositAddress'], info['disabled'],
                                info['delisted'], info['frozen']))

        g.db.connection.commit()
        return r

    def returnMarketTradeHistory(self, currencyPair: str, start: int, end: int) -> object:
        return poloniexApi.returnMarketTradeHistory(currencyPair, start, end)

    def actualizePairs(self, currencyPair: str, start: int, end: int, period: int) -> object:
        self.updateCurrencies()

        if ((end - start) // period) > MAX_DATA_IN_SINGLE_QUERY:
            pass
