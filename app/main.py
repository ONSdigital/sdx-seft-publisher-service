#!/usr/bin/env python3
#   encoding: UTF-8

import argparse
import base64
from collections import OrderedDict
import json
import logging
import os.path
import sys
import uuid

from sdc.rabbit.publisher import QueuePublisher
from sdc.rabbit.exceptions import PublishMessageError
from sdx.common.logger_config import logger_initial_config
import tornado.ioloop
import tornado.web

from app.encrypter import Encrypter
from app.ftpclient import FTPWorker
from app.settings import BATCH_SIZE


class StatusService(tornado.web.RequestHandler):

    def initialize(self, work):
        self.recent = {n: v for n, v in enumerate(Task.recent)}

    def get(self):
        self.write(self.recent)


class Task:
    recent = OrderedDict([])

    @staticmethod
    def amqp_params(services):
        queue = os.getenv("SEFT_PUBLISHER_RABBIT_QUEUE", "Seft.CollectionInstruments")
        try:
            uri = services["rabbitmq"][0]["credentials"]["protocols"]["amqp"]["uri"]
        except (IndexError, KeyError):
            uri = "amqp://{user}:{password}@{hostname}:{port}/{vhost}".format(
                hostname=os.getenv("SEFT_RABBITMQ_HOST", "localhost"),
                port=os.getenv("SEFT_RABBITMQ_PORT", 5672),
                user=os.getenv("SEFT_RABBITMQ_DEFAULT_USER", "guest"),
                password=os.getenv("SEFT_RABBITMQ_DEFAULT_PASS", "guest"),
                vhost=os.getenv("SEFT_RABBITMQ_DEFAULT_VHOST", "%2f")
            )
        return {
            "amqp_url": uri,
            "queue_name": queue,
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
            "user": os.getenv("SEFT_FTP_USER", "ons"),
            "password": os.getenv("SEFT_FTP_PASS", "ons"),
            "host": os.getenv("SEFT_FTP_HOST", "127.0.0.1"),
            "port": int(os.getenv("SEFT_FTP_PORT", 2021)),
            "working_directory": os.getenv("SEFT_PUBLISHER_FTP_FOLDER", ".")
        }

    def __init__(self, args, services):
        self.args = args
        self.services = services
        amqp_details = self.amqp_params(services)
        self.publisher = QueuePublisher(urls=[amqp_details.get('amqp_url')], queue=amqp_details.get('queue_name'))

    def transfer_files(self):
        log = logging.getLogger("sdx-seft-publisher-service")

        log.info("Looking for files...")
        worker = FTPWorker(**self.ftp_params(self.services))
        encrypter = Encrypter(**self.encrypt_params(self.services, locn=self.args.keys))
        with worker as active:
            if not active:
                return

            try:
                for _ in range(0, BATCH_SIZE):
                    job = active.get_file(active.filenames.pop())

                    data = job._asdict()
                    data["file"] = base64.standard_b64encode(job.file).decode("ascii")
                    data["ts"] = job.ts.isoformat()
                    payload = encrypter.encrypt(data)

                    headers = {'tx_id': str(uuid.uuid4())}

                    try:
                        self.publisher.publish_message(payload, headers=headers)
                    except PublishMessageError:
                        log.info("Failed to publish {0}".format(job.filename))
                    else:
                        log.info("Published {0}".format(job.filename))
                        active.delete(job.filename)
                        log.info("Deleted {0}".format(job.filename))
            except IndexError:
                pass


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

    # Create the API service
    app = make_app()
    app.listen(args.port)

    # Create the scheduled task
    interval_ms = int(os.getenv("SEFT_FTP_INTERVAL_MS", 1000))
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
    loop.start()
    return 0


if __name__ == "__main__":
    p = parser()
    args = p.parse_args()
    rv = main(args)
    sys.exit(rv)
