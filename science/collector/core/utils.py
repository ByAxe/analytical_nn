import calendar
import datetime

from flask import make_response

JSON_MIME_TYPE = 'application/json'
MAX_DATA_IN_SINGLE_QUERY: int = 50000

CURRENCIES_INSERT_PLAN_SQL = """
PREPARE currencies_insert_plan AS
    INSERT INTO poloniex.currencies
    (id, symbol, name, min_conf, deposit_address, disabled, delisted, frozen)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)"""

CHART_DATA_INSERT_PLAN_SQL = """
PREPARE chart_data_insert_plan AS
    INSERT INTO poloniex.chart_data
    (main_currency, secondary_currency, period, date, high, low, open, close, volume, quote_volume, weighted_average)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)"""

PERIODS = [300, 900, 1800, 7200, 14400, 86400]
WINDOWS = ['HOUR', 'DAY', 'WEEK', 'MONTH']

KEY = "WCLZAVGZ-YPHP8DR7-LWXQCEQ6-4DIKZNKM"
SECRET = "af6163ddd2cd1b55e771c45c981a46c9bb77de553c75e6862af41b00cb3f5c5f1fced0767741b575492d844d83482b18fd8336efc1e8d33b19691ff719ea3033"

ALL = 'all'
PAUSE_BETWEEN_QUERIES_SECONDS = .200

CYCLE_PARAMETERS = {
    "budget": 0.00030000,
    "pairs": [
        "ETH_BCH",
        "ETH_ZRX",
        "ETH_STEEM",
        "ETH_ZEC"
    ],
    "risk": 70,
    "window": {
        "MONTH": 1
    },
    "period": 300,
    "steps": 1,
    "common_currency": "ETH",
    "THRESHOLD": 0.00000050,
    "current_price_from": "last",
    "learn_on": "weightedAverage",
    "reopen": False,
    "top_n": 3,
    "algorithm": "SARIMA",
    "hyperparameters": {
        "SARIMA": {
            "P": 1,
            "D": 0,
            "Q": 2,
            "s": 12
        },
        "ARIMA": {
            "P": 1,
            "D": 0,
            "Q": 2
        }
    }
}


def search_book(books, book_id):
    for book in books:
        if book['id'] == book_id:
            return book


def json_response(data='', status=200, headers=None):
    headers = headers or {}
    if 'Content-Type' not in headers:
        headers['Content-Type'] = JSON_MIME_TYPE

    return make_response(data, status, headers)


def datetimeToTimestamp(date_time: datetime):
    return str(calendar.timegm(date_time.timetuple()))
