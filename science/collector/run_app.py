import os

from science.collector.api.poloniex_public_controller import app

if __name__ == '__main__':
    # app.debug = True
    app.config['DATABASE_NAME'] = "dbname=deep_crypto user=postgres password=postgres host=localhost port=5432"
    host = os.environ.get('IP', '0.0.0.0')
    port = int(os.environ.get('PORT', 9090))
    app.run(host=host, port=port)
