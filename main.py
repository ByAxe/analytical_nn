from science.collector.controller.poloniex_controller import app

if __name__ == '__main__':
    # app.debug = True
    app.run(host='127.0.0.1', port=9000, debug=False)
