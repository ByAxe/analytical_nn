import os

from science.collector.api.poloniex_public_controller import app

# from science.collector.api._03_post_method import app
# from science.collector.api._04_delete_method import app
# from science.collector.api._05_flask_restful_simple import app


if __name__ == '__main__':
    # app.debug = True
    app.config['DATABASE_NAME'] = 'pq://postgres:postgres@localhost:5432/deep_crypto'
    host = os.environ.get('IP', '0.0.0.0')
    port = int(os.environ.get('PORT', 9090))
    app.run(host=host, port=port)
