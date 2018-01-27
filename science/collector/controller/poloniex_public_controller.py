# from flask_restful import Resource, Api
import json

import psycopg2
from flask import Flask, g, request

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
    g.cur = g.connection.cursor()


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

    if ('start' or 'end') in request.args:
        error = json.dumps({'error': 'Missing field (start or end). If you want to specify the range - mention both '
                                     'bounds'})
        return json_response(error, 400)

    currencyPair: str = request.args['currencyPair']
    start, end = None, None

    if ('start' and 'end') in request.args:
        start: int = request.args['start']
        end: int = request.args['end']

    r = poloniexPublicService.returnMarketTradeHistory(currencyPair, start, end)

    return json_response(str(r))


@app.route('/public/chartdata/<string:main_currency>/<string:secondary_currency>')
def loadChartData(main_currency, secondary_currency):
    if ('start' and 'end' and 'period') not in request.args:
        error = json.dumps({'error': 'Missing field/s (currencyPair, start, end, period)'})
        return json_response(error, 400)

    r = poloniexPublicService.actualizePairs(main_currency, secondary_currency,
                                             int(request.args['start']), int(request.args['end']),
                                             int(request.args['period']))

    return json_response(str(r))


@app.errorhandler(404)
def not_found(e):
    return e, 404
