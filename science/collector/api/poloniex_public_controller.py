import postgresql
from flask import Flask, g

from science.collector.api.utils import json_response
from science.collector.poloniex import Poloniex

app = Flask(__name__)

books = [{
    'id': 33,
    'title': 'The Raven',
    'author_id': 1
}]


@app.before_request
def before_request():
    g.db = postgresql.open(app.config['DATABASE_NAME'])


@app.route('/currencies', methods=['PUT'])
def update_currencies():
    poloniex = Poloniex("APIKey", "Secret".encode())

    r = poloniex.returnCurrencies()

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

    return json_response(status=200)
