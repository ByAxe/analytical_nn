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

        # one more time - filter by restrictions of the api
        filtered_plan_without_duplicates = self.filterPlanByRestrictions(plan_without_duplicates)

        return filtered_plan_without_duplicates

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
        plan_d = plan
        unique_operations = []

        # juxtapose each operations with each and find all duplicated operations for pairs
        for operation in plan:
            for operation_d in plan_d:
                # if this is the same operation
                if operation == operation_d:
                    continue

                # in our case it means that we must collapse them into one operation
                if operation_d.pair == operation.pair:
                    # increase the amount
                    operation.amount += operation_d.amount

                    # choose optimal price among predictions
                    if (operation.op_type == 'BUY' and operation_d.price < operation.price) or (
                            operation.op_type == 'SELL' and operation_d.price > operation.price):
                        operation.price = operation_d.price

            # check if this pair already present in unique operations
            # because with our logic we will collapse all operations with the same pair,
            # once we met it in outer loop
            is_present = False
            for unique_op in unique_operations:
                is_present = unique_op.pair == operation.pair

            # insert this operations with accumulated amount and best price among all similar
            if not is_present:
                unique_operations.append(operation)

        return unique_operations

    def filterPlanByRestrictions(self, plan) -> list:
        """
        TODO insert docs
        :param plan:
        :return:
        """
        filtered_plan = []

        # filter the operations by restrictions of poloniex api
        for operation in plan:
            amount = operation.amount

            # if it is not filled yet -> calculate amount for operation
            if not amount:
                amount = self.calculateAmountForOperation(operation)

            secondary_currency = operation.pair.split("_")[1]
            secondary_balance = float(self.balances[secondary_currency])

            # if we have less amount of currency than can possibly operate with - reduce it to affordable maximum
            if amount > secondary_balance:
                amount = secondary_balance

            total = round(amount * operation.price, 8)

            # if total is less than TOTAL_MINIMUM ==> operation won't be approved by Poloniex API
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
