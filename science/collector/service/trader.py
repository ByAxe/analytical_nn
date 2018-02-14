import math

from science.collector.core.entities import Operation
from science.collector.core.utils import ALL
from science.collector.service.poloniex_service import PoloniexPublicService


class Trader:
    poloniex_service: PoloniexPublicService
    budget, fee, top_n, risk, steps, pairs, predictions, common_currency, THRESHOLD = 0.0, 0.0, 0, 0, 0, [], {}, '', 0
    ticker, balances, tradeHistory, orders, current_price = {}, {}, {}, {}, ''

    def __init__(self, poloniex_service, budget, steps, pairs, predictions, risk=0, fee=0.25, top_n=3,
                 common_currency='BTC', THRESHOLD=0.000001, current_price='lowerAsk'):
        """
        :param predictions: from model that makes predictions
        :param current_price: the field from ticker to rely on while calculating profitability between current price and predicted one
        :param THRESHOLD: the baseline of profitability to perform any operation
        :param common_currency: what is the common currency
        :param top_n: how many of most profitable operations to apply
        :param fee: percentage of fee from operation
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
        self.fee = fee
        self.top_n = top_n
        self.common_currency = common_currency
        self.THRESHOLD = THRESHOLD
        self.current_price = current_price
        self.predictions = predictions

        # get the current prices from poloniex
        self.ticker = self.poloniex_service.returnTickerForPairs(self.pairs)

        # What is currently on balance
        self.balances = self.poloniex_service.returnBalances()

        # Get trade history for account
        self.tradeHistory = self.poloniex_service.returnTradeHistory(ALL)

        # Return all open orders for account
        self.orders = self.poloniex_service.returnOpenOrders(ALL)

    def preparePlan(self) -> list:
        """
        Prepares a plan, based on:
            A) What is currently bought
            B) Whether there are still open orders
            C) Given predictions
            D) Current situation on market (on-line sells and buys)
        :return: prepared plan
        """
        common_plan = {}

        # iterate through all the pairs and predicted steps and find all appropriate operations to make
        for step in range(1, self.steps + 1):
            plan_for_step = []
            for pair, prediction_list in self.predictions.items():
                predicted_price = prediction_list[step]
                current_price = self.ticker[pair][self.current_price]

                _current_delta = current_price - predicted_price
                _current_delta = self.minus_fee(_current_delta)
                current_delta = self.to_common_currency(_current_delta, pair)

                # If delta less than the stated threshold --> do nothing!
                if math.fabs(current_delta) <= self.THRESHOLD:
                    continue
                # If delta less than 0 --> we must buy currency now
                # Example: current = 2, predicted = 4, delta = -2, so we must buy it now for 2, to sell later for 4
                elif current_delta < 0:
                    plan_for_step.append(Operation('BUY', pair, current_delta, step))

                # Find an average price for that this currency was bought
                tradeHistoryForPair: list = self.tradeHistory[pair]

                # TODO define when we should do this calculation based on trading history AND balances
                if tradeHistoryForPair:
                    bought_for = self.calculate_avg_price(tradeHistoryForPair)

                    # TODO Reopen orders with new price
                    openOrdersForPair = self.orders[pair]

                    # TODO calculate when it should be sold relying on price we have bought it for previously

            common_plan[step] = plan_for_step

        for step, plan in common_plan.items():
            # sort by delta (profitability metrics)
            plan.sort(key=lambda op: op.delta, reverse=True)

            # leave only top_n operations
            common_plan[step] = plan[:self.top_n]

        resulting_plan = []

        # Manage risk for the steps
        if self.steps > 1 and self.risk > 0:
            # in how many steps we believe as if it must happen
            _believe_in = round(self.steps * self.risk / 100)
            believe_in = 1 if _believe_in == 0 else _believe_in

            # collect all operations from all believed steps into one list
            for step, plan in common_plan.items():
                if step > believe_in:
                    continue
                resulting_plan.extend(plan)

            # select only top_n of them by profitability
            resulting_plan.sort(key=lambda op: op.delta, reverse=True)
            resulting_plan = resulting_plan[:self.top_n]
        else:
            resulting_plan = common_plan[1]

        return resulting_plan

    def trade(self, plan: list) -> dict:
        """
        Performs an operations if needed based on previously prepared plan
        :return: performed operations
        """
        # TODO implement
        return {}

    def to_common_currency(self, amount, pair):
        """
        Converts amount to some common currency
        :param amount:
        :param pair: currency pair
        :return: the same amount converted to common currency
        """
        # TODO implement to get a possibility to trade with respect to a few main currencies
        return amount

    def calculate_avg_price(self, tradeHistory: list) -> dict:
        """
        Calculate all remainders for that currency was bought and collect it into dictionary
        :param tradeHistory: history of all transactions for particular currency pair
        :return: {rate1: remainder1, rate2: remainder2, ...}
        """
        remainders_dict = {}

        # Sort them by relevance
        tradeHistory.sort(key=lambda k: k['globalTradeID'])

        total, previous_rate, remainder = 0, 0, 0
        for record in tradeHistory:
            _type, amount = record['type'], float(record['amount'])
            # Fee doesn't included in 'total' so we must add fee and then divide by amount to get fair rate
            rate = (float(record['total']) + float(record['fee'])) / amount

            if _type == 'buy':
                # If total > than 0 it means that we made a BUY while still have some
                # So we have to account the price and remainder of previously bought currency
                if total > 0:
                    remainders_dict[previous_rate] = remainder

                total += amount
            elif _type == 'sell':
                total -= amount

                # If total < than 0 it means that we also sold a previously bought currency
                if total < 0:
                    # so we have to iterate though all our remainders and remove them one by one
                    # until our total is equal to 0
                    on_del = []
                    for _rate, _remainder in remainders_dict.items():
                        # if we sold more than we have in this remainder just add it to total and remove element from results
                        if math.fabs(total) >= _remainder:
                            total += _remainder
                            on_del.append(_rate)
                        # If our total becomes less than current remainder
                        # just subtract it from the remainder and set zero to total
                        else:
                            remainders_dict[_rate] += total
                            total = 0
                            break

                    # remove all closed remainders
                    for _del in on_del:
                        del remainders_dict[_del]

            previous_rate, remainder = rate, total

        # Calculate average price for remainders
        average_price = sum(remainders_dict.keys()) / float(len(remainders_dict))

        return average_price

    def minus_fee(self, delta):
        """
        Subtracts fee from delta
        :param delta: basic difference
        :return: difference minus fee for operation
        """
        return delta - (delta * self.fee) / 100
