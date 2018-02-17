import hashlib
import hmac
import json
import time
from urllib.parse import urlencode
from urllib.request import urlopen


def createTimeStamp(datestr, format="%Y-%m-%d %H:%M:%S"):
    return time.mktime(time.strptime(datestr, format))


class Poloniex:
    def __init__(self, APIKey, Secret):
        self.APIKey = APIKey
        self.Secret = Secret

    def post_process(self, before):
        after = before

        # Add timestamps if there isnt one but is a datetime
        if 'return' in after:
            if isinstance(after['return'], list):
                for x in range(0, len(after['return'])):
                    if isinstance(after['return'][x], dict):
                        if 'datetime' in after['return'][x] and 'timestamp' not in after['return'][x]:
                            after['return'][x]['timestamp'] = float(createTimeStamp(after['return'][x]['datetime']))

        return after

    def api_query(self, command, req=None):

        if req is None:
            req = {}
        if command == "returnTicker" or command == "return24Volume" or command == "returnCurrencies":
            ret = urlopen('https://poloniex.com/public?command=' + command)
            return json.loads(ret.read())
        elif command == "returnOrderBook":
            ret = urlopen(
                'https://poloniex.com/public?command=' + command + '&currencyPair=' + str(req['currencyPair']))
            return json.loads(ret.read())
        elif command == "returnMarketTradeHistory":
            if all([req['start'], req['end']]):
                ret = urlopen(
                    'https://poloniex.com/public?command=' + "returnTradeHistory"
                    + '&currencyPair=' + str(req['currencyPair'])
                    + '&start=' + str(req['start'])
                    + '&end=' + str(req['end'])
                )
            else:
                ret = urlopen(
                    'https://poloniex.com/public?command=' + "returnTradeHistory" + '&currencyPair=' + str(
                        req['currencyPair']))
            return json.loads(ret.read())
        elif command == "returnChartData":
            ret = urlopen(
                'https://poloniex.com/public?command=' + command
                + '&currencyPair=' + str(req['currencyPair'])
                + '&start=' + str(req['start'])
                + '&end=' + str(req['end'])
                + '&period=' + str(req['period'])
            )
            return json.loads(ret.read())
        else:
            req['command'] = command
            req['nonce'] = int(time.time() * 1000)
            post_data = urlencode(req)

            sign = hmac.new(self.Secret, post_data, hashlib.sha512).hexdigest()
            headers = {
                'Sign': sign,
                'Key': self.APIKey
            }

            ret = urlopen('https://poloniex.com/tradingApi', post_data, headers)
            jsonRet = json.loads(ret.read())
            return self.post_process(jsonRet)

    def returnTicker(self) -> dict:
        return self.api_query("returnTicker")

    def return24Volume(self):
        return self.api_query("return24Volume")

    def returnOrderBook(self, currencyPair):
        return self.api_query("returnOrderBook", {'currencyPair': currencyPair})

    def returnMarketTradeHistory(self, currencyPair: str, start: int = None, end: int = None) -> list:
        return self.api_query("returnMarketTradeHistory",
                              {"currencyPair": currencyPair, 'start': start, 'end': end})

    def returnChartData(self, currencyPair: str, start: int, end: int, period: int) -> list:
        return self.api_query("returnChartData",
                              {'currencyPair': currencyPair, 'start': start, 'end': end, 'period': period})

    def returnCurrencies(self) -> dict:
        return self.api_query("returnCurrencies")

    # Returns all of your balances.
    # Outputs:
    # {"BTC":"0.59098578","LTC":"3.31117268", ... }
    def returnBalances(self):
        return self.api_query('returnBalances')

    # Returns your open orders for a given market, specified by the "currencyPair" POST parameter, e.g. "BTC_XCP"
    # Inputs:
    # currencyPair  The currency pair e.g. "BTC_XCP"
    # Outputs:
    # orderNumber   The order number
    # type          sell or buy
    # rate          Price the order is selling or buying at
    # Amount        Quantity of order
    # total         Total value of order (price * quantity)
    def returnOpenOrders(self, currencyPair):
        return self.api_query('returnOpenOrders', {"currencyPair": currencyPair})

    # Returns your trade history for a given market, specified by the "currencyPair" POST parameter
    # Inputs:
    # currencyPair  The currency pair e.g. "BTC_XCP"
    # Outputs:
    # date          Date in the form: "2014-02-19 03:44:59"
    # rate          Price the order is selling or buying at
    # amount        Quantity of order
    # total         Total value of order (price * quantity)
    # type          sell or buy
    def returnTradeHistory(self, currencyPair, start, end, limit):
        return self.api_query('returnTradeHistory',
                              {"currencyPair": currencyPair, "start": start, "end": end, "limit": limit})

    def returnFeeInfo(self):
        """
        If you are enrolled in the maker-taker fee schedule, returns your current trading fees
        and trailing 30-day volume in BTC. This information is updated once every 24 hours.
        Example:
        {"makerFee": "0.00140000", "takerFee": "0.00240000", "thirtyDayVolume": "612.00248891", "nextTier": "1200.00000000"}
        :return: your current trading fees
        """
        return self.api_query('returnFeeInfo')

    # Places a buy order in a given market. Required POST parameters are "currencyPair", "rate", and "amount". If
    # successful, the method will return the order number.
    # Inputs: currencyPair  The current pair rate price the order is buying at amount
    # Amount of coins to buy Outputs: orderNumber   The order number
    def buy(self, currencyPair, rate, amount, fillOrKill=0, immediateOrCancel=0, postOnly=0):
        return self.api_query('buy', {"currencyPair": currencyPair, "rate": rate, "amount": amount,
                                      "fillOrKill": fillOrKill, "immediateOrCancel": immediateOrCancel,
                                      'postOnly': postOnly})

    # Places a sell order in a given market. Required POST parameters are "currencyPair", "rate", and "amount". If
    # successful, the method will return the order number. Inputs: currencyPair  The current pair rate          price
    #  the order is selling at amount        Amount of coins to sell Outputs: orderNumber   The order number
    def sell(self, currencyPair, rate, amount, fillOrKill=0, immediateOrCancel=0, postOnly=0):
        return self.api_query('sell', {"currencyPair": currencyPair, "rate": rate, "amount": amount,
                                       "fillOrKill": fillOrKill, "immediateOrCancel": immediateOrCancel,
                                       'postOnly': postOnly})

    # Cancels an order you have placed in a given market. Required POST parameters are "currencyPair" and "orderNumber".
    # Inputs:
    # currencyPair  The current pair
    # orderNumber   The order number to cancel
    # Outputs:
    # success        1 or 0
    def cancel(self, currencyPair, orderNumber):
        return self.api_query('cancelOrder', {"currencyPair": currencyPair, "orderNumber": orderNumber})

    # Immediately places a withdrawal for a given currency, with no email confirmation. In order to use this method,
    # the withdrawal privilege must be enabled for your API key. Required POST parameters are "currency", "amount",
    # and "address". Sample output: {"response":"Withdrew 2398 NXT."} Inputs: currency      The currency to withdraw
    # amount        The amount of this coin to withdraw address       The withdrawal address Outputs: response
    # Text containing message about the withdrawal
    def withdraw(self, currency, amount, address):
        return self.api_query('withdraw', {"currency": currency, "amount": amount, "address": address})


def main():
    p = Poloniex("APIKey", "Secret".encode())
    r = p.returnCurrencies()
    print(r)


if __name__ == '__main__':
    main()