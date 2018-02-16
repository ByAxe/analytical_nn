from science.collector.core.entities import Operation
from science.collector.core.utils import ALL
from science.collector.service.poloniex_service import PoloniexPublicService


class Trader:
    poloniex_service: PoloniexPublicService
    budget, top_n, risk, steps, pairs, predictions, common_currency, THRESHOLD = 0.0, 0, 0, 0, [], {}, '', 0
    ticker, balances, tradeHistory, orders, current_price, takerFee, makerFee, = {}, {}, {}, {}, '', 0.0, 0.0

    def __init__(self, poloniex_service, budget, steps, pairs, predictions, risk=0, top_n=3,
                 common_currency='BTC', THRESHOLD=0.000001, current_price_from='lowerAsk', reopen=False):
        """
        :param predictions: from model that makes predictions
        :param reopen: whether we must reopen all previously opened orders with new iteration if the currency coincide
        :param current_price_from: the field from ticker to rely on while calculating profitability between current price and predicted one
        :param THRESHOLD: the baseline of profitability to perform any operation
        :param common_currency: what is the common currency
        :param top_n: how many of most profitable operations to apply
        :param pairs: all pair for that prediction made
        :param steps: amount of steps in future on that prediction made
        :param risk: The number of steps that a trader will count on when building a plan,
        :param budget: allowed overall maximum (measured in BTC) for all operations during the iteration
        as what exactly should happen. Measured in %.
        :param poloniex_service: wrapper for interaction with poloniex api
        """
        self.reopen = reopen
        self.poloniex_service = poloniex_service
        self.budget = budget
        self.risk = 100 if risk > 100 else 0 if risk < 0 else risk
        self.steps = steps
        self.pairs = pairs
        self.top_n = top_n
        self.common_currency = common_currency
        self.THRESHOLD = THRESHOLD
        self.current_price_from = current_price_from
        self.predictions = predictions

        # get the current prices from poloniex
        self.ticker = self.poloniex_service.returnTickerForPairs(self.pairs)

        # What is currently on balance
        self.balances = self.poloniex_service.returnBalances()

        # Get trade history for account
        self.tradeHistory = self.poloniex_service.returnTradeHistory(ALL)

        # Return all open orders for account
        self.orders = self.poloniex_service.returnOpenOrders(ALL)

        # Obtain current fees for operations from market
        fees = self.poloniex_service.returnFeeInfo()
        self.makerFee, self.takerFee = fees['makerFee'], fees['takerFee']

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
                main_currency, secondary_currency = pair.split('_')

                predicted_price = prediction_list[step]
                current_price = self.ticker[pair][self.current_price_from]

                # get delta between current
                buy_profit = self.get_delta(two=current_price, one=predicted_price, pair=pair, op_type='BUY')

                # If profit more than threshold and 0 --> we must buy currency now
                # Example: current = 2, predicted = 4, profit = 2, so we must buy it now for 2, to sell later for 4
                if buy_profit > 0 and buy_profit > self.THRESHOLD:
                    plan_for_step.append(Operation('BUY', pair, buy_profit, step, predicted_price))
                    continue

                # Find an average price for this currency was bought
                tradeHistoryForPair: list = self.tradeHistory[pair]

                main_balance = float(self.balances[main_currency])
                secondary_balance = float(self.balances[secondary_currency])

                # if we already have on balance this currency so we must investigate the price for what it was bought
                if secondary_balance > 0.0:
                    bought_for = self.calculate_avg_price(tradeHistoryForPair, secondary_balance)

                    # calculate profit of selling it NOW relying on price we have bought it for previously
                    current_sell_profit = self.get_delta(two=bought_for, one=current_price, pair=pair,
                                                         op_type='SELL')

                    # calculate profit of selling it LATER relying on price we have bought it for previously
                    predicted_sell_profit = self.get_delta(two=bought_for, one=predicted_price, pair=pair,
                                                           op_type='SELL')

                    # If profit more than threshold and 0 --> we must sell currency now
                    if predicted_sell_profit > 0 and predicted_sell_profit > self.THRESHOLD:
                        plan_for_step.append(Operation('SELL', pair, predicted_sell_profit, step, predicted_price))

                    # If profit more than threshold and 0 --> we must sell currency now
                    if step == 1 and current_sell_profit > 0 and current_sell_profit > self.THRESHOLD:
                        plan_for_step.append(Operation('SELL', pair, current_sell_profit, step, current_price))

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

    def trade(self, plan: list) -> list:
        """
        Performs an operations if needed based on previously prepared plan
        :return: performed operations
        """
        performed_operations = []

        for operation in plan:
            # if there is an open orders for the currencies we have planned to buy or sell -> cancel previously opened order
            if self.reopen:
                for order in self.orders[operation.pair] or []:
                    if order['type'].upper() == operation.op_type:
                        self.poloniex_service.cancelOrder(order['orderNumber'])

            amount = round(self.budget / self.top_n, 8)

            performed_operation = self.poloniex_service.operate(operation=operation.op_type,
                                                                currencyPair=operation.pair,
                                                                rate=operation.price,
                                                                amount=amount)
            performed_operations.append(performed_operation)

        return performed_operations

    def to_common_currency(self, amount, pair):
        """
        Converts amount to some common currency
        :param amount: of currency
        :param pair: currency pair
        :return: the same amount converted to common currency
        """
        # TODO implement to get a possibility to trade with respect to a few main currencies
        return amount

    def calculate_avg_price(self, tradeHistory: list, balance: float) -> float:
        """
        Calculate all remainders for that currency was bought and collect it into dictionary
        :param balance: current balance for the right currency
        :param tradeHistory: history of all transactions for particular currency pair
        :return: avg price from all remainders
        """
        remainders_dict = {}

        # Sort them by relevance
        tradeHistory.sort(key=lambda k: k['globalTradeID'], reverse=True)
        _balance = balance
        for record in tradeHistory:
            _type, amount, operation_total, fee = record['type'], float(record['amount']), float(record['total']), \
                                                  float(record['fee'])

            # if it is not buy operation -> we do not interested in it
            # because we need to find out for what price we have bought the amount of this currency, that we have now
            if _type != 'buy':
                continue

            # Fee doesn't included in 'total' so we must add fee and then divide by amount to get fair rate
            rate = (operation_total + fee) / amount

            # If current operation does not explain why do we have so many coins on balance...
            if _balance > operation_total:
                # add this amount with this rate into our dictionary
                remainders_dict[rate] = operation_total

                # and subtract it from balance
                _balance -= operation_total

            # or - if total of current operation >= than balance, just return current rate as average price for left coins
            else:
                return rate

            # Calculate average price for remainders
            average_price = sum(remainders_dict.keys()) / float(len(remainders_dict))

            return average_price

    def minus_fee(self, delta, op_type):
        """
        Subtracts fee from delta
        :param op_type: type of operation differs by fee cost
        :param delta: basic difference
        :return: difference minus fee for operation
        """
        fee = self.takerFee if op_type == 'BUY' else self.makerFee
        return delta - (delta * fee) / 100

    def get_delta(self, one, two, pair, op_type):
        # simple difference between two numbers
        __current_delta = one - two

        # minus fee
        _current_delta = self.minus_fee(__current_delta, op_type)

        # convert to common currency
        current_delta = self.to_common_currency(_current_delta, pair)
        return current_delta
