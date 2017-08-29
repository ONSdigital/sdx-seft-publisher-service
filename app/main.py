#!/usr/bin/env python3
#   encoding: UTF-8

import argparse
import base64
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import datetime
import json
import logging
import os.path
import sys
import uuid

from sdx.common.logger_config import logger_initial_config
import tornado.ioloop
import tornado.web
from tornado.httpclient import AsyncHTTPClient, HTTPError

from encrypter import Encrypter
from ftpclient import FTPWorker
from publisher import DurableTopicPublisher


class HealthCheckService(tornado.web.RequestHandler):

    def initialize(self, task):
        self.task = task

    def get(self):
        rabbit_health = False
        if self.task.rabbit_check.done():
            try:
                self.task.rabbit_check.result()
            except (HTTPError, Exception):
                # HTTPError is raised for non-200 responses
                # Also possible IOError, etc
                pass
            else:
                rabbit_health = True

        ftp_health = self.task.ftp_check.done() and self.ftp_check.result()

        self.write({
            "status": rabbit_health and ftp_health,
            "dependencies": {
                "rabbitmq": rabbit_health,
                "ftp": ftp_health
            }
        })


class StatusService(tornado.web.RequestHandler):

    def initialize(self, task):
        self.recent = {n: v for n, v in enumerate(task.recent)}

    def get(self):
        self.write(self.recent)


class Task:
    recent = OrderedDict([])

    @staticmethod
    def amqp_params(services):
        check = os.getenv("RABBIT_HEALTHCHECK_URL")
        queue = os.getenv("SEFT_PUBLISHER_RABBIT_QUEUE", "Seft.CollectionInstruments")
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
            "queue_name": queue,
            "check": check
        }

    @staticmethod
    def encrypt_params(services, locn="."):
        log = logging.getLogger("sdx-seft-publisher-service")
        pub_fp = os.getenv("RAS_SEFT_PUBLISHER_PUBLIC_KEY",
                           os.path.join(locn, "test_no_password.pub"))
        priv_fp = os.getenv("SDX_SEFT_PUBLISHER_PRIVATE_KEY",
                            os.path.join(locn, "test_no_password.pem"))
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
        }
        return rv

    @staticmethod
    def ftp_params(services):
        return {
            "user": os.getenv("SEFT_FTP_USER", "user"),
            "password": os.getenv("SEFT_FTP_PASS", "password"),
            "host": os.getenv("SEFT_FTP_HOST", "127.0.0.1"),
            "port": int(os.getenv("SEFT_FTP_PORT", 2121)),
            "working_directory": os.getenv("SEFT_PUBLISHER_FTP_FOLDER", "/")
        }

    def __init__(self, args, services):
        self.args = args
        self.services = services
        self.publisher = DurableTopicPublisher(**self.amqp_params(services))
        self.executor = ThreadPoolExecutor()
        self.rabbit_check = None
        self.ftp_check = None

    def check_services(self, ftp_params={}):
        http_client = AsyncHTTPClient()
        params = self.amqp_params(self.services)
        self.rabbit_check = http_client.fetch(params["check"])

        ftp = FTPWorker(**(ftp_params or self.ftp_params(self.services)))
        self.ftp_check = self.executor.submit(ftp.check)

    def transfer_files(self):
        log = logging.getLogger("sdx-seft-publisher-service")
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
                if job.filename not in self.recent:
                    data = job._asdict()
                    data["file"] = base64.standard_b64encode(job.file).decode("ascii")
                    data["ts"] = job.ts.isoformat()
                    payload = encrypter.encrypt(data)

                    headers = {'tx_id': str(uuid.uuid4())}

                    msg_id = self.publisher.publish_message(payload, headers=headers)
                    self.recent[job.filename] = (job.ts, msg_id)
                    log.info("Published {0}".format(job.filename))

            now = datetime.datetime.utcnow()
            for fn, (ts, msg_id) in self.recent.copy().items():
                if msg_id not in self.publisher._deliveries:
                    active.delete(fn)
                    log.info("Deleted {0}".format(fn))
                if now - ts > datetime.timedelta(hours=1):
                    del self.recent[fn]


def make_app(task):
    return tornado.web.Application([
        ("/healthcheck", HealthCheckService, {"task": task}),
        ("/recent", StatusService, {"task": task}),
    ])


def parser(description="SEFT Publisher service."):
    here = os.path.dirname(__file__)
    p = argparse.ArgumentParser(description)
    p.add_argument(
        "--keys", default=os.path.abspath(os.path.join(here, "test")),
        help="Set a path to the keypair directory.")
    p.add_argument(
        "--port", type=int, default=int(os.getenv("SDX_SEFT_PUBLISHER_PORT", "8080")),
        help="Set a port for the service.")
    return p


def main(args):
    name = "sdx-seft-publisher-service"
    logger_initial_config(
        service_name=name,
        log_level=os.getenv("LOGGING_LEVEL", "DEBUG")
    )
    log = logging.getLogger(name)
    log.info("Launched in {0}.".format(os.getcwd()))

    services = json.loads(os.getenv("VCAP_SERVICES", "{}"))
    task = Task(args, services)

    # Create the API service
    app = make_app(task)
    app.listen(args.port)

    # Create the scheduled task
    transfer_ms = int(os.getenv("SEFT_FTP_INTERVAL_MS", 30 * 60 * 1000))
    transfer = tornado.ioloop.PeriodicCallback(
        task.transfer_files,
        transfer_ms,
    )

    transfer.start()
    log.info("Transfer scheduled.")

    check_ms = 5 * 60 * 1000
    check = tornado.ioloop.PeriodicCallback(
        task.check_services,
        check_ms,
    )
    check.start()
    log.info("Check scheduled.")

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
