class Parameters:
    budget: float
    pairs: list
    risk: int
    window: dict
    period: int
    steps: int

    def __init__(self, params):
        """
        - Budget: allowed overall maximum (measured in USD) for all operations during the iteration
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
        :param params: parameters as dictionary
        """
        self.budget = params['budget']
        self.pairs = params['pairs']
        self.risk = params['risk']
        self.window = params['window']
        self.period = params['period']
        self.steps = params['steps']
