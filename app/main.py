#!/usr/bin/env python3
#   encoding: UTF-8

import argparse
from collections import deque
import json
import logging
from logging.handlers import WatchedFileHandler
import os.path
import sys

import tornado.ioloop
import tornado.web

from encrypter import Encrypter
from ftpclient import FTPWorker
from publisher import DurableTopicPublisher


class StatusService(tornado.web.RequestHandler):

    def initialize(self, work):
        self.recent = {n: v for n, v in enumerate(Task.recent)}

    def get(self):
        self.write(self.recent)


class Task:
    recent = deque(maxlen=24)

    @staticmethod
    def amqp_params(services):
        return {
            "amqp_url": os.getenv("RABBIT_URL"),
            "queue_name": "Seft.Responses",
        }

    @staticmethod
    def encrypt_params(services, locn="."):
        log = logging.getLogger("sdx.seft.crypt")
        pub_fp = os.path.join(locn, "test_no_password.pub")
        priv_fp = os.path.join(locn, "test_no_password.pem")
        priv_key = None
        pub_key = None
        try:
            with open(priv_fp, "r") as key_file:
                priv_key = key_file.read()
        except:
            log.warning("Could not read key {0}".format(priv_fp))
        try:
            with open(pub_fp, "r") as key_file:
                pub_key = key_file.read()
        except:
            log.warning("Could not read key {0}".format(pub_fp))

        rv = {
            "public_key": pub_key,
            "private_key": priv_key,
            "private_key_password": None,
        }
        return rv

    @staticmethod
    def ftp_params(services):
        return {
            "user": "testuser",
            "password": "password",
            "host": "127.0.0.1",
            "port": 2121,
        }

    def __init__(self, args, services):
        self.args = args
        self.services = services

    def transfer_files(self):
        log = logging.getLogger("sdx.seft")
        log.info("Looking for files...")
        log.info(vars(self.args))
        worker = FTPWorker(**self.ftp_params(self.services))
        publisher = DurableTopicPublisher(**self.amqp_params(self.services))
        encrypter = Encrypter(**self.encrypt_params(self.services, locn=self.args.keys))
        with worker as active:
            for job in active.get(active.filenames):
                while True:
                    payload = encrypter.encrypt(job.contents)
                    if not publisher.publish_message(payload):
                        continue

                while True:
                    if not active.delete(job.fn):
                        continue

                self.recent.append((job.ts.isoformat(), job.fn))


def make_app():
    return tornado.web.Application([
        (r"/recent", StatusService, {"work": Task}),
    ])


def parser(description="SEFT Publisher service."):
    here = os.path.dirname(__file__)
    p = argparse.ArgumentParser(description)
    p.add_argument(
        "-v", "--verbose", required=False,
        action="store_const", dest="log_level",
        const=logging.DEBUG, default=logging.INFO,
        help="Increase the verbosity of output")
    p.add_argument(
        "--keys", default=os.path.abspath(os.path.join(here, "test")),
        help="Set a path to the keypair directory.")
    p.add_argument(
        "--port", type=int, default=int(os.getenv("PORT", "8080")),
        help="Set a port for the service.")
    p.add_argument(
        "--log", default=None, dest="log_path",
        help="Set a file path for log output")
    return p


def configure_log(args, name="sdx.seft"):
    log = logging.getLogger(name)
    log.setLevel(args.log_level)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s|%(message)s")
    ch = logging.StreamHandler()

    if args.log_path is None:
        ch.setLevel(args.log_level)
    else:
        fh = WatchedFileHandler(args.log_path)
        fh.setLevel(args.log_level)
        fh.setFormatter(formatter)
        log.addHandler(fh)
        ch.setLevel(logging.WARNING)

    ch.setFormatter(formatter)
    log.addHandler(ch)
    log = logging.getLogger("pika")
    log.setLevel(args.log_level)
    log.addHandler(ch)
    return name


def main(args):
    log = logging.getLogger(configure_log(args))
    log.info("Launched in {0}.".format(os.getcwd()))

    log.info(os.listdir("app/test"))
    services = json.loads(os.getenv("VCAP_SERVICES", "{}"))

    # Create the API service
    app = make_app()
    app.listen(args.port)

    # Create the scheduled task
    interval_ms = 30 * 60 * 1000
    task = Task(args, services)
    sched = tornado.ioloop.PeriodicCallback(
        task.transfer_files,
        interval_ms,
    )

    sched.start()
    log.info("Scheduler started.")

    # Perform the first transfer immediately
    loop = tornado.ioloop.IOLoop.current()
    loop.spawn_callback(task.transfer_files)
    loop.start()
    return 0

if __name__ == "__main__":
    p = parser()
    args = p.parse_args()
    rv = main(args)
    sys.exit(rv)
