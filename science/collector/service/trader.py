import collections

from science.collector.core.entities import Operation
from science.collector.core.utils import ALL, TOTAL_MINIMUM
from science.collector.service.poloniex_service import PoloniexPublicService


class Trader:
    poloniex_service: PoloniexPublicService
    budget, top_n, risk, steps, pairs, predictions, common_currency, THRESHOLD = 0.0, 0, 0, 0, [], {}, '', 0
    ticker, balances, tradeHistory, orders, current_price, takerFee, makerFee, = {}, {}, {}, {}, '', 0.0, 0.0

    def __init__(self, poloniex_service, budget, steps, pairs, predictions, risk=0, top_n=3,
                 common_currency='BTC', THRESHOLD=0.000001, current_price_buy_from='last',
                 current_price_sell_from='last', reopen=False):
        """
        :param predictions: from model that makes predictions
        :param reopen: whether we must reopen all previously opened orders with new iteration if the currency coincide
        :param current_price_buy_from: the field from ticker to rely on while calculating profitability between current price and predicted one when buying
        :param current_price_sell_from: the field from ticker to rely on while calculating profitability between current price and predicted one when selling
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
        self.current_price_buy_from = current_price_buy_from
        self.current_price_sell_from = current_price_sell_from

        for p in predictions:
            for k, v in p.items():
                self.predictions[k] = v

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
        self.makerFee, self.takerFee = float(fees['makerFee']), float(fees['takerFee'])

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

                current_price_buy = float(self.ticker[pair][self.current_price_buy_from])
                current_price_sell = float(self.ticker[pair][self.current_price_sell_from])

                # get delta between current
                buy_profit = self.get_delta(two=current_price_buy, one=predicted_price, pair=pair, op_type='BUY')

                # If profit more than threshold and 0 --> we must buy currency now
                # Example: current = 2, predicted = 4, profit = 2, so we must buy it now for 2, to sell later for 4
                if buy_profit > 0 and buy_profit > self.THRESHOLD:
                    plan_for_step.append(Operation(op_type='BUY', pair=pair, profit=buy_profit,
                                                   step=step, price=current_price_buy))
                    continue

                # Find an average price for this currency was bought
                tradeHistoryForPair: list = self.tradeHistory.get(pair, None)

                main_balance = float(self.balances[main_currency])
                secondary_balance = float(self.balances[secondary_currency])

                # if we already have on balance this currency so we must investigate the price for what it was bought
                if tradeHistoryForPair and secondary_balance > 0.0:
                    bought_for = self.calculate_avg_price(tradeHistoryForPair, secondary_balance)

                    # calculate profit of selling it NOW relying on price we have bought it for previously
                    current_sell_profit = self.get_delta(two=bought_for, one=current_price_sell, pair=pair,
                                                         op_type='SELL')

                    # calculate profit of selling it LATER relying on price we have bought it for previously
                    predicted_sell_profit = self.get_delta(two=bought_for, one=predicted_price, pair=pair,
                                                           op_type='SELL')

                    # If predicted profit more than threshold and 0 --> we must place an order to sell currency
                    if predicted_sell_profit > 0 and predicted_sell_profit > self.THRESHOLD:
                        plan_for_step.append(Operation(op_type='SELL', pair=pair, profit=predicted_sell_profit,
                                                       step=step, price=predicted_price, orderType=False))

                    # If profit more than threshold and 0 --> we must sell currency now
                    if step == 1 and current_sell_profit > 0 and current_sell_profit > self.THRESHOLD:
                        plan_for_step.append(Operation(op_type='SELL', pair=pair, profit=current_sell_profit, step=step,
                                                       price=current_price_sell))

            common_plan[step] = plan_for_step

        # Filter operations and remove all those are not appropriate for poloniex or not the most profitable
        for step, plan in common_plan.items():
            filtered_plan = self.filterPlanByRestrictions(plan)

            # sort by delta (profitability metrics)
            filtered_plan.sort(key=lambda op: op.delta, reverse=True)

            # leave only top_n operations
            common_plan[step] = filtered_plan[:self.top_n]

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

        # remove all duplicated operations
        plan_without_duplicates = self.removeDuplicates(resulting_plan)

        return plan_without_duplicates

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

            performed_operation = self.poloniex_service.operate(operation=operation.op_type,
                                                                currencyPair=operation.pair,
                                                                rate=operation.price,
                                                                amount=operation.amount,
                                                                orderType=operation.orderType)
            performed_operations.append(performed_operation)
            print('Performed operation:', performed_operation)

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
            _type, amount, operation_total, fee, rate = record['type'], float(record['amount']), float(record['total']), \
                                                        float(record['fee']), float(record['rate'])

            # if it is not buy operation -> we do not interested in it
            # because we need to find out for what price we have bought the amount of this currency, that we have now
            if _type != 'buy':
                continue

            # Fee doesn't included in 'total'
            rate += rate * fee / 100

            # If current operation does not explain why do we have so many coins on balance...
            if _balance > amount:
                # add this amount with this rate into our dictionary
                remainders_dict[rate] = amount

                # and subtract it from balance
                _balance -= amount

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
        __current_delta = float(one) - float(two)

        # minus fee
        _current_delta = self.minus_fee(__current_delta, op_type)

        # convert to common currency
        current_delta = self.to_common_currency(_current_delta, pair)
        return current_delta

    def removeDuplicates(self, plan: list) -> list:
        """
        TODO insert docs
        :param plan:
        :return:
        """
        pairs = [o.pair for o in plan]

        # find duplicates in plan
        duplicated_pairs = [item for item, count in collections.Counter(pairs).items() if count > 1]

        duplicated_operations = dict.fromkeys(duplicated_pairs)

        # Go though all operations to find duplicates and then collect them into dictionary
        #  with lower/higher price planned for particular pair, based on type of operation (buy/sell)
        for operation in plan:
            if operation.pair in duplicated_pairs:
                planned_operation: dict = duplicated_operations[operation.pair]

                planned_operation['amount'] = planned_operation.get('amount', 0) + operation.amount

                # if we buy -> pick a lowest possible price we've predicted
                if operation.op_type == 'BUY':
                    planned_operation['rate'] = operation.price \
                        if operation.price < planned_operation.get('rate', 0) \
                        else planned_operation.get('rate', 0)

                # if we sell -> pick a higher possible price we've predicted
                elif operation.op_type == 'SELL':
                    planned_operation['price'] = operation.price \
                        if operation.price > planned_operation.get('price', 0) \
                        else planned_operation.get('price', 0)

                duplicated_operations[operation.pair] = planned_operation

        plan_without_duplicates = []

        for operation in plan:
            if operation.pair not in duplicated_pairs:
                plan_without_duplicates.append(operation)
            else:
                operation.price = duplicated_operations[operation.pair]['price']
                operation.amount = duplicated_operations[operation.pair]['amount']


        return plan

    def filterPlanByRestrictions(self, plan) -> list:
        """
        TODO insert docs
        :param plan:
        :return:
        """
        filtered_plan = []

        # filter the operations by restrictions of poloniex api
        for operation in plan:
            amount = self.calculateAmountForOperation(operation)

            # if we have less amount of currency than can possibly operate with - reduce it to affordable maximum
            secondary_currency = operation.pair.split("_")[1]
            secondary_balance = float(self.balances[secondary_currency])
            amount = secondary_balance if amount > secondary_balance else amount

            total = round(amount * operation.price, 8)

            # if total is less than TOTAL_MINIMUM -> operation won't be approved by api
            if total >= TOTAL_MINIMUM:
                operation.amount = amount
                filtered_plan.append(operation)

        return filtered_plan

    def calculateAmountForOperation(self, operation):
        """
        TODO insert docs
        :param operation:
        :return:
        """
        return round(self.budget / operation.price / self.top_n, 8)
