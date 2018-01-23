import os

from science.collector.api._01_manual_response_class import app

# from science.collector.api._02_make_response_helper import app
# from science.collector.api._03_post_method import app
# from science.collector.api._04_delete_method import app
# from science.collector.api._05_flask_restful_simple import app


if __name__ == '__main__':
    # app.debug = True
    # app.config['DATABASE_NAME'] = 'library.db'
    host = os.environ.get('IP', '0.0.0.0')
    port = int(os.environ.get('PORT', 9090))
    app.run(host=host, port=port)
