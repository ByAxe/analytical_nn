# from flask_restful import Resource, Api
import json

import psycopg2
from flask import Flask, g, request
from psycopg2.extras import DictCursor

from science.collector.core.utils import json_response
from science.collector.service.poloniex_public_service import PoloniexPublicService

app = Flask(__name__)
poloniexPublicService = PoloniexPublicService()


@app.before_request
def before_request():
    """
    Initializes everything before the first request
    Works similar to post-construct phase in Java
    """
    g.connection = psycopg2.connect(app.config['DATABASE_NAME'])
    g.cur = g.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)


@app.route('/public/currencies', methods=['PUT'])
def updateCurrencies():
    """
    Synchronizes list of currencies with poloniex api
    :return: elements those were updated
    """

    r = poloniexPublicService.updateCurrencies()

    return json_response(str(r))


@app.route('/public/trade/history')
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


@app.route('/public/chartdata')
def getChartData():
    main_currency = request.args['main_currency'] if 'main_currency' in request.args else None
    secondary_currency = request.args['secondary_currency'] if 'secondary_currency' in request.args else None
    start = request.args['start'] if 'start' in request.args else None
    end = request.args['end'] if 'end' in request.args else None
    period = request.args['period'] if 'period' in request.args else None
    fields = request.args['fields'].split(',') if 'fields' in request.args else None
    limit = request.args['limit'] if 'limit' in request.args else None

    result = poloniexPublicService.getChartData(main_currency, secondary_currency, start, end, period,
                                                fields=fields,
                                                limit=limit)
    return json_response(str(result))


@app.route('/public/csv/chartdata')
def saveChartDataToCSV():
    main_currency = request.args['main_currency'] if 'main_currency' in request.args else None
    secondary_currency = request.args['secondary_currency'] if 'secondary_currency' in request.args else None
    start = request.args['start'] if 'start' in request.args else None
    end = request.args['end'] if 'end' in request.args else None
    period = request.args['period'] if 'period' in request.args else None

    poloniexPublicService.saveChartDataToCSV(main_currency, secondary_currency, start, end, period)
    return json_response()


@app.errorhandler(404)
def not_found(e):
    return e, 404
