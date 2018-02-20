from science.collector.core.utils import TOTAL_MINIMUM


class Parameters:
    params: dict
    budget: float
    pairs: list
    risk: int
    window: dict
    period: int
    steps: int
    top_n: int
    common_currency: str
    THRESHOLD: float
    current_price_buy_from: str
    current_price_sell_from: str
    learn_on: str
    reopen: bool
    hyperparameters: dict
    algorithm: str

    def __init__(self, params):
        """
        - params: save the whole dictionary
        - Budget: allowed overall maximum (measured in BTC) for all operations during the iteration
        - Pairs: the list of pairs among those algorithm creates a plan
        - Risk: The number of steps that a trader will count on when building a plan,
            as what exactly should happen. Measured in %.
            Risk = 100% means that algorithm will count on farthest predicted step,
                as if it must happen.
            Risk = 0% means that algorithm only counts on the closest predicted step
        - Window: window of data on that prediction will be made
            Example: {'WEEK':2}
        - Period: periodicity of predicted data
        - Steps: amount of steps in future (periods) on that prediction will be made
        - top_n: how many of most profitable operations to apply
        - common_currency: what is the common currency for accounting profitability
        - THRESHOLD: the baseline of profitability to perform any operation
        - current_price_buy_from: the field from ticker to rely on while calculating profitability between current price and predicted one when buying
        - current_price_sell_from: the field from ticker to rely on while calculating profitability between current price and predicted one when selling
        - learn_on: the column from chartData from poloniex on that to learn on our prediction algorithm
        - reopen: whether we should reopen all still opened orders on sells or buys?
        - hyperparameters: dictionary of hyperparameters for prediction model
            Example: {'SARIMA': {'P': 1, 'D': 0, 'Q': 2, 's': 12}, 'ARIMA': {'P': 1, 'D': 0, 'Q': 2}, ...}
        - algorithm: what algorithm to use for prediction
        :param params: parameters as dictionary
        """
        self.params = params

        self.budget = params['budget']
        self.pairs = params['pairs']
        self.risk = params['risk']
        self.window = params['window']
        self.period = params['period']
        self.steps = params['steps']
        self.top_n = params['top_n']
        self.common_currency = params['common_currency']
        self.THRESHOLD = params['THRESHOLD']
        self.current_price_buy_from = params['current_price_buy_from']
        self.current_price_sell_from = params['current_price_sell_from']
        self.learn_on = params['learn_on']
        self.reopen = params['reopen']
        self.hyperparameters = params['hyperparameters']
        self.algorithm = params['algorithm']

    def __str__(self):
        return self.params.__str__()


class Operation:
    op_type: str
    pair: str
    delta: float
    step: int
    price: float
    orderType: str
    amount: float

    def __init__(self, op_type, pair, profit, step, price, amount=TOTAL_MINIMUM, orderType='immediateOrCancel'):
        """
        DTO for operation
        :param price: what is predicted price
        :param op_type: type of the operation (SELL or BUY)
        :param pair: currency pair
        :param profit: profitability of operation
        :param step: in how many steps in future it should happen
        """
        self.op_type = op_type
        self.pair = pair
        self.delta = profit
        self.step = step
        self.price = price
        self.orderType = orderType
        self.amount = amount

    def __str__(self):
        return "Operation{operation_type = %s, pair = %s, delta = %s, step = %s, price = %s, amount=%s, orderType=%s}" \
               % (self.op_type, self.pair, self.delta, self.step, self.price, self.amount, self.orderType)
