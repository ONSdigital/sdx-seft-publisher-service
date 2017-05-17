import atexit
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask import Flask, jsonify
from structlog import wrap_logger

import publisher
import settings

__version__ = '0.0.1'

app = Flask(__name__)

logging.basicConfig(level=settings.LOGGING_LEVEL, format=settings.LOGGING_FORMAT)
logger = wrap_logger(logging.getLogger(__name__))

logger.info("START", version=__version__)

scheduler = BackgroundScheduler()
scheduler.start()

scheduler.add_job(
    func=publisher.run,
    trigger=IntervalTrigger(seconds=5),
    id='checking_ftp',
    name='Check FTP for files every 5 seconds',
    replace_existing=True)

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown(wait=False))

@app.errorhandler(500)
def ftp_error(e):
    logger.error("FTP Error")
    message = {
        'valid': False,
        'status': 500,
        'message': "FTP Endpoint error"
    }

    resp = jsonify(message)
    resp.status_code = 500
    return resp


@app.route('/healthcheck', methods=['GET'])
def healthcheck():
    if not publisher.conn():
        return ftp_error()
    else:
        return jsonify({'status': 'ok'})


if __name__ == '__main__':
    port = int(os.getenv("PORT"))
    app.run(debug=True, host='0.0.0.0', port=port)
