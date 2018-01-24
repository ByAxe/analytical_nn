import postgresql
from flask import Flask, g, request
# from flask_restful import Resource, Api
import json
from science.collector.api.utils import json_response
from science.collector.poloniex import Poloniex

app = Flask(__name__)


@app.before_request
def before_request():
    g.db = postgresql.open(app.config['DATABASE_NAME'])


@app.route('/public/currencies', methods=['PUT'])
def update_currencies():
    """
    Synchronizes list of currencies with poloniex api
    :return: elements those were updated
    """
    poloniex = Poloniex("APIKey", "Secret".encode())

    r = poloniex.returnCurrencies()

    # clear the table
    g.db.execute("DELETE FROM poloniex.currencies")

    # insert all the data
    ins = g.db.prepare(
        "INSERT INTO poloniex.currencies "
        "(id, symbol, name, min_conf, deposit_address, disabled, delisted, frozen) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)")

    for symbol, info in r.items():
        identifier: int = info['id']
        name: str = info['name']
        min_conf: int = info['minConf']
        deposit_address = info['depositAddress']
        disabled: int = info['disabled']
        delisted: int = info['delisted']
        frozen: int = info['frozen']

        ins(identifier, symbol, name, min_conf, deposit_address, disabled, delisted, frozen)

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

    poloniex = Poloniex("APIKey", "Secret".encode())
    r = poloniex.returnMarketTradeHistory(currencyPair, start, end)

    return json_response(str(r))


@app.errorhandler(404)
def not_found(e):
    return e, 404
