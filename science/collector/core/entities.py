class Parameters:
    budget: float
    pairs: list
    risk: int
    window: dict
    period: int
    steps: int
    top_n: int
    common_currency: str
    THRESHOLD: float
    current_price_from: str
    learn_on: str
    reopen: bool
    hyperparameters: dict

    def __init__(self, params):
        """
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
        - current_price_from: the field from ticker to rely on while calculating profitability between current price and predicted one
        - learn_on: the column from chartData from poloniex on that to learn on our prediction algorithm
        - reopen: whether we should reopen all still opened orders on sells or buys?
        - hyperparameters: dictionary of hyperparameters for prediction model
            Example: {'SARIMA': {'P': 1, 'D': 0, 'Q': 2, 's': 12}, 'ARIMA': {'P': 1, 'D': 0, 'Q': 2}, ...}
        :param params: parameters as dictionary
        """
        self.budget = params['budget']
        self.pairs = params['pairs']
        self.risk = params['risk']
        self.window = params['window']
        self.period = params['period']
        self.steps = params['steps']
        self.top_n = params['top_n']
        self.common_currency = params['common_currency']
        self.THRESHOLD = params['THRESHOLD']
        self.current_price_from = params['current_price']
        self.learn_on = params['learn_on']
        self.reopen = params['reopen']
        self.hyperparameters = params['hyperparameters']


class Operation:
    op_type: str
    pair: str
    delta: float
    step: int
    price: float

    def __init__(self, op_type, pair, profit, step, price):
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
