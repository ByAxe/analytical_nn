# from flask_restful import Resource, Api
import json

import psycopg2
from flask import Flask, g, request

from science.collector.api.utils import json_response
from science.collector.poloniex import Poloniex

app = Flask(__name__)
poloniex = Poloniex("APIKey", "Secret".encode())


@app.before_request
def before_request():
    """
    Initializes everything before the first request
    Works similar to post-construct phase in Java
    """
    g.db = psycopg2.connect(app.config['DATABASE_NAME'])
    g.cur = g.db.cursor()


@app.route('/public/currencies', methods=['PUT'])
def update_currencies():
    """
    Synchronizes list of currencies with poloniex api
    :return: elements those were updated
    """

    r = poloniex.returnCurrencies()

    # clear the table
    g.cur.execute("DELETE FROM poloniex.currencies")

    # prepares the query for insert
    g.cur.execute("PREPARE currencies_insert_plan AS " +
                  "INSERT INTO poloniex.currencies "
                  "(id, symbol, name, min_conf, deposit_address, disabled, delisted, frozen) "
                  "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)")

    sql = "EXECUTE currencies_insert_plan (%s, %s, %s, %s, %s, %s, %s, %s)"

    # actual insert into DB
    for symbol, info in r.items():
        g.cur.execute(sql, (info['id'], symbol, info['name'],
                            info['minConf'], info['depositAddress'], info['disabled'],
                            info['delisted'], info['frozen']))

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

    r = poloniex.returnMarketTradeHistory(currencyPair, start, end)

    return json_response(str(r))


@app.route('/public/ticker')
def actualizePairs():
    if ('currencyPair' and 'start' and 'end' and 'period') not in request.args:
        error = json.dumps({'error': 'Missing field/s (currencyPair, start, end, period)'})
        return json_response(error, 400)


    pass


@app.errorhandler(404)
def not_found(e):
    return e, 404
