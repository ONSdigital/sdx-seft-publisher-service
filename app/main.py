#!/usr/bin/env python3
#   encoding: UTF-8

import argparse
import base64
from collections import OrderedDict
import datetime
import json
import logging
from logging.handlers import WatchedFileHandler
import multiprocessing
import os.path
import sys
import tempfile
import time

from sdx.common.logger_config import logger_initial_config
import tornado.ioloop
import tornado.web

from encrypter import Encrypter
from ftpclient import FTPWorker
from publisher import DurableTopicPublisher
import test.localserver


class StatusService(tornado.web.RequestHandler):

    def initialize(self, work):
        self.recent = {n: v for n, v in enumerate(Task.recent)}

    def get(self):
        self.write(self.recent)


class Task:
    recent = OrderedDict([])

    @staticmethod
    def amqp_params(services):
        try:
            uri = services["rabbitmq"][0]["credentials"]["protocols"]["amqp"]["uri"]
        except (IndexError, KeyError):
            uri = "amqp://{user}:{password}@{hostname}:{port}/{vhost}".format(
                hostname=os.getenv("SEFT_RABBITMQ_HOST", "localhost"),
                port=os.getenv("SEFT_RABBITMQ_PORT", 5672),
                user=os.getenv("SEFT_RABBITMQ_DEFAULT_USER", "rabbit"),
                password=os.getenv("SEFT_RABBITMQ_DEFAULT_PASS", "rabbit"),
                vhost=os.getenv("SEFT_RABBITMQ_DEFAULT_VHOST", "%2f")
            )
        return {
            "amqp_url": uri,
            "queue_name": "Seft.Responses",
        }

    @staticmethod
    def encrypt_params(services, locn="."):
        log = logging.getLogger("sdx-seft-publisher")
        pub_fp = os.getenv("RAS_SEFT_PUBLIC_KEY", os.path.join(locn, "test_no_password.pub"))
        priv_fp = os.getenv("SDX_SEFT_PRIVATE_KEY", os.path.join(locn, "test_no_password.pem"))
        priv_key = None
        pub_key = None
        try:
            with open(priv_fp, "r") as key_file:
                priv_key = key_file.read()
        except Exception as e:
            log.warning("Could not read key {0}".format(priv_fp))
            log.warning(e)
        try:
            with open(pub_fp, "r") as key_file:
                pub_key = key_file.read()
        except Exception as e:
            log.warning("Could not read key {0}".format(pub_fp))
            log.warning(e)

        rv = {
            "public_key": pub_key,
            "private_key": priv_key,
            "private_key_password": os.getenv("SDX_SEFT_PRIVATE_KEY_PASSWORD", None),
        }
        return rv

    @staticmethod
    def ftp_params(services):
        return {
            "user": os.getenv("SEFT_FTP_USER", "user"),
            "password": os.getenv("SEFT_FTP_PASS", "password"),
            "host": os.getenv("SEFT_FTP_HOST", "127.0.0.1"),
            "port": os.getenv("SEFT_FTP_PORT", 2121),
        }

    def __init__(self, args, services):
        self.args = args
        self.services = services
        self.publisher = DurableTopicPublisher(**self.amqp_params(services))

    def transfer_files(self):
        log = logging.getLogger("sdx-seft-publisher")
        if not self.publisher.publishing:
            log.warning("Publisher is not ready.")
            return

        log.info("Looking for files...")
        worker = FTPWorker(**self.ftp_params(self.services))
        encrypter = Encrypter(**self.encrypt_params(self.services, locn=self.args.keys))
        with worker as active:
            if not active:
                return

            for job in active.get(active.filenames):
                if job.fn not in self.recent:
                    data = job._asdict()
                    data["contents"] = base64.standard_b64encode(job.contents).decode("ascii")
                    data["ts"] = job.ts.isoformat()
                    payload = encrypter.encrypt(data)
                    msg_id = self.publisher.publish_message(payload)
                    self.recent[job.fn] = (job.ts, msg_id)
                    log.info("Published {0}".format(job.fn))

            now = datetime.datetime.utcnow()
            for fn, (ts, msg_id) in self.recent.copy().items():
                if msg_id not in self.publisher._deliveries:
                    active.delete(fn)
                    log.info("Deleted {0}".format(fn))
                if now - ts > datetime.timedelta(hours=1):
                    del self.recent[fn]


def make_app():
    return tornado.web.Application([
        (r"/recent", StatusService, {"work": Task}),
    ])


def parser(description="SEFT Publisher service."):
    here = os.path.dirname(__file__)
    p = argparse.ArgumentParser(description)
    p.add_argument(
        "--keys", default=os.path.abspath(os.path.join(here, "test")),
        help="Set a path to the keypair directory.")
    p.add_argument(
        "--port", type=int, default=int(os.getenv("PORT", "8080")),
        help="Set a port for the service.")
    p.add_argument(
        "--test", default=False, action="store_true",
        help="Configure for functional test.")
    return p


def main(args):
    name = "sdx-seft-publisher"
    logger_initial_config(
        service_name=name,
        log_level=os.getenv("LOGGING_LEVEL", "DEBUG")
    )
    log = logging.getLogger(name)
    log.info("Launched in {0}.".format(os.getcwd()))

    services = json.loads(os.getenv("VCAP_SERVICES", "{}"))

    if args.test:
        locn = tempfile.mkdtemp()
        with tempfile.NamedTemporaryFile(suffix=".xls", dir=locn, delete=False) as f:
            f.write(os.urandom(4096))

        server = multiprocessing.Process(
            target=test.localserver.serve,
            args=(locn,),
            kwargs=Task.ftp_params(services)
        )
        server.start()
        time.sleep(5)

    # Create the API service
    app = make_app()
    app.listen(args.port)

    # Create the scheduled task
    interval_ms = int(os.getenv("SEFT_FTP_INTERVAL_MS", 30 * 60 * 1000))
    task = Task(args, services)
    sched = tornado.ioloop.PeriodicCallback(
        task.transfer_files,
        interval_ms,
    )

    sched.start()
    log.info("Scheduler started.")

    # Perform the first transfer immediately
    loop = tornado.ioloop.IOLoop.current()
    loop.call_later(6, task.transfer_files)
    task.publisher.run()
    return 0

if __name__ == "__main__":
    p = parser()
    args = p.parse_args()
    rv = main(args)
    sys.exit(rv)
