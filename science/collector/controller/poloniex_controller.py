# from flask_restful import Resource, Api
import json
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask, request

from science.collector.core.utils import json_response, CYCLE_PARAMETERS
from science.collector.service.cycle_service import Cycle
from science.collector.service.poloniex_service import PoloniexPublicService

app = Flask(__name__)
poloniexPublicService: PoloniexPublicService = None
cycle: Cycle = None


@app.before_request
def before_request():
    """
    Initializes everything before the first request
    Works similar to post-construct phase in Java
    """
    global poloniexPublicService, cycle
    poloniexPublicService = PoloniexPublicService()
    cycle = Cycle(poloniexPublicService)


@app.route('/public/currencies', methods=['PUT'])
def updateCurrencies():
    """
    Synchronizes list of currencies with poloniex api
    :return: elements those were updated
    """

    r = poloniexPublicService.updateCurrencies()

    return json_response(str(r))


@app.route('/public/trade/history', methods=['GET'])
def loadMarketTradeHistory():
    """
    Loads market data trades history for specified currencyPair.
    Optionally may be specified upper and lower bounds for synchronizing
    in request arguments
    :return: elements those were found for request
    """
    if 'currencyPair' not in request.args:
        error = json.dumps({'error': 'Missing field (currencyPair)'})
        return json_response(error, 400)

    if ('start' or 'end') not in request.args:
        error = json.dumps({'error': 'Missing field (start or end). If you want to specify the range - mention both '
                                     'bounds'})
        return json_response(error, 400)

    currencyPair = request.args['currencyPair']

    start = int(request.args['start']) if 'start' in request.args else None
    end = int(request.args['end']) if 'end' in request.args else None

    r = poloniexPublicService.returnMarketTradeHistory(currencyPair, start, end)

    return json_response(str(r))


@app.route('/public/chartdata/<string:main_currency>/<string:secondary_currency>', methods=['PUT'])
def loadChartData(main_currency, secondary_currency):
    if ('start' and 'end') not in request.args:
        error = json.dumps({'error': 'Missing field/s (start, end)'})
        return json_response(error, 400)

    period = int(request.args['period']) if 'period' in request.args else None

    r = poloniexPublicService.loadChartData(main_currency, secondary_currency,
                                            int(request.args['start']), int(request.args['end']),
                                            period)

    return json_response(str(r))


@app.route('/public/chartdata', methods=['DELETE'])
def deleteChartData():
    main_currency = request.args['main_currency'] if 'main_currency' in request.args else None
    secondary_currency = request.args['secondary_currency'] if 'secondary_currency' in request.args else None
    start = request.args['start'] if 'start' in request.args else None
    end = request.args['end'] if 'end' in request.args else None
    period = request.args['period'] if 'period' in request.args else None

    poloniexPublicService.deleteChartData(main_currency, secondary_currency, start, end, period)

    return json_response()


@app.route('/public/chartdata', methods=['GET'])
def getChartData():
    main_currency = request.args['main_currency'] if 'main_currency' in request.args else None
    secondary_currency = request.args['secondary_currency'] if 'secondary_currency' in request.args else None
    start = request.args['start'] if 'start' in request.args else None
    end = request.args['end'] if 'end' in request.args else None
    period = request.args['period'] if 'period' in request.args else None
    fields = request.args['fields'].split(',') if 'fields' in request.args else None
    limit = request.args['limit'] if 'limit' in request.args else None

    result = poloniexPublicService.getChartDataFromDB(main_currency, secondary_currency, start, end, period,
                                                      fields=fields,
                                                      limit=limit)
    return json_response(str(result))


@app.route('/public/csv/chartdata', methods=['GET'])
def saveChartDataToCSV():
    main_currency = request.args['main_currency'] if 'main_currency' in request.args else None
    secondary_currency = request.args['secondary_currency'] if 'secondary_currency' in request.args else None
    start = request.args['start'] if 'start' in request.args else None
    end = request.args['end'] if 'end' in request.args else None
    period = request.args['period'] if 'period' in request.args else None

    poloniexPublicService.saveChartDataToCSV(main_currency, secondary_currency, start, end, period)
    return json_response()


@app.route('/private/iteration', methods=['POST'])
def startCycleIteration():
    """
    Fires the cycle iteration of trading on poloniex with given parameters
    :return: success if everything is OK, and fail if not OR it is already running
    """
    # Extract incoming params from request
    params = request.get_json()

    # pass everything to service method
    operations = cycle.startCycleIteration(params)

    #  return created plan and made operations
    return json_response(str(operations))


def job():
    cycle.startCycleIteration(params_dict=CYCLE_PARAMETERS)


@app.route('/private/cycle', methods=['POST'])
def fireCycle():
    scheduler = BackgroundScheduler()

    scheduler.add_job(job, CronTrigger.from_crontab('25/5 * * * *'))
    scheduler.start()

    return json_response()


@app.errorhandler(404)
def not_found(e):
    return e, 404


@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500
