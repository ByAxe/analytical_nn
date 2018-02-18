from science.collector.controller.poloniex_controller import app
from science.collector.core.utils import CYCLE_PARAMETERS
from science.collector.service.cycle_service import Cycle
from science.collector.service.poloniex_service import PoloniexPublicService


def job():
    poloniexPublicService = PoloniexPublicService()
    cycle = Cycle(poloniexPublicService)

    cycle.startCycleIteration(params_dict=CYCLE_PARAMETERS)


if __name__ == '__main__':
    # app.debug = True
    app.run(host='127.0.0.1', port=9000, debug=False)
    # schedule.every(5).minutes.do(job)
