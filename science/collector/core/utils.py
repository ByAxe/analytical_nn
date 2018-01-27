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


def search_book(books, book_id):
    for book in books:
        if book['id'] == book_id:
            return book


def json_response(data='', status=200, headers=None):
    headers = headers or {}
    if 'Content-Type' not in headers:
        headers['Content-Type'] = JSON_MIME_TYPE

    return make_response(data, status, headers)
