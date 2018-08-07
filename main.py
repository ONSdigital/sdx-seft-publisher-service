#!/usr/bin/env python3

import argparse
import base64
import datetime
import json
import os.path
import sys
import tornado.ioloop
import tornado.web
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from tornado.httpclient import AsyncHTTPClient, HTTPError

from app import create_and_wrap_logger
from app.encrypter import Encrypter
from app.ftpclient import FTPWorker
from app.publisher import DurableTopicPublisher

DEFAULT_FTP_INTERVAL_MS = 10 * 60 * 1000

log = create_and_wrap_logger(__name__)


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
        queue = "Seft.CollectionInstruments"
        try:
            uri = services["rabbitmq"][0]["credentials"]["protocols"]["amqp"]["uri"]
        except (IndexError, KeyError):
            uri = "amqp://{user}:{password}@{hostname}:{port}/{vhost}".format(
                hostname=os.getenv("SEFT_RABBITMQ_HOST", "localhost"),
                port=os.getenv("SEFT_RABBITMQ_PORT", 5672),
                user=os.getenv("SEFT_RABBITMQ_DEFAULT_USER", "guest"),
                password=os.getenv("SEFT_RABBITMQ_DEFAULT_PASS", "guest"),
                vhost="%2f"
            )
        check = "http://{user}:{password}@{hostname}:{port}/api/healthchecks/node".format(
            user=os.getenv("SEFT_RABBITMQ_MONITORING_USER", "monitor"),
            password=os.getenv("SEFT_RABBITMQ_MONITORING_PASS", "monitor"),
            hostname=os.getenv("SEFT_RABBITMQ_HOST", "localhost"),
            port=os.getenv("SEFT_RABBITMQ_HEALTHCHECK_PORT", 15672)
        )

        return {
            "amqp_url": uri,
            "queue_name": queue,
            "check": check
        }

    @staticmethod
    def encrypt_params(services, locn="."):
        log.info("Encrypt params")
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
            log.warning(str(e))
        try:
            with open(pub_fp, "r") as key_file:
                pub_key = key_file.read()
        except Exception as e:
            log.warning("Could not read key {0}".format(pub_fp))
            log.warning(str(e))

        rv = {
            "public_key": pub_key,
            "private_key": priv_key,
        }
        log.info("End of encrypt_params")
        return rv

    @staticmethod
    def ftp_params(services):
        return {
            "user": os.getenv("SEFT_FTP_USER", "ons"),
            "password": os.getenv("SEFT_FTP_PASS", "ons"),
            "host": os.getenv("SEFT_FTP_HOST", "127.0.0.1"),
            "port": int(os.getenv("SEFT_FTP_PORT", 2021)),
            "working_directory": os.getenv("SEFT_PUBLISHER_FTP_FOLDER", "/")
        }

    def __init__(self, args, services):
        self.args = args
        self.services = services
        self.publisher = DurableTopicPublisher(**self.amqp_params(services))
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.rabbit_check = None
        self.ftp_check = None
        self.transfer = False

    def check_services(self, ftp_params=None, rabbit_url=""):
        ftp_params = ftp_params or self.ftp_params(self.services)
        http_client = AsyncHTTPClient()
        params = self.amqp_params(self.services)
        self.rabbit_check = http_client.fetch(rabbit_url or params["check"])

        ftp = FTPWorker(**ftp_params)
        self.ftp_check = self.executor.submit(ftp.check)

    def transfer_files(self):

        if not self.publisher.publishing:
            log.warning("Publisher is not ready.")
            return

        if self.transfer:
            log.warning("Cancelling overlapped task.")
            return
        else:
            self.transfer = True

        try:
            log.info("Looking for files...")
            worker = FTPWorker(**self.ftp_params(self.services))
            log.info("So its signed in successfully")
            log.info(self.services)
            log.info(self.ar)
            encrypter = Encrypter(**self.encrypt_params(self.services, locn=self.args.keys))
            with worker as active:
                if not active:
                    log.info("Worker not active")
                    return

                for job in active.get(active.filenames):
                    if job.filename not in self.recent:
                        data = job._asdict()
                        data["file"] = base64.standard_b64encode(job.file).decode("ascii")
                        data["ts"] = job.ts.isoformat()
                        payload = encrypter.encrypt(data)

                        headers = {'tx_id': str(uuid.uuid4())}

                        msg_id = self.publisher.publish_message(payload, headers=headers)
                        if msg_id is None:
                            log.warning("Failed to publish {0}".format(job.filename))
                        else:
                            self.recent[job.filename] = (job.ts, msg_id)
                            log.info("Published {0}".format(job.filename))

                now = datetime.datetime.utcnow()
                for fn, (ts, msg_id) in self.recent.copy().items():
                    if msg_id in self.publisher._deliveries:
                        active.delete(fn)
                        log.info("Deleted {0}".format(fn))

                    refresh_time = 2 * int(os.getenv("SEFT_FTP_INTERVAL_MS", DEFAULT_FTP_INTERVAL_MS))
                    if now - ts > datetime.timedelta(milliseconds=refresh_time):
                        del self.recent[fn]
        finally:
            self.transfer = False


def make_app(task):
    return tornado.web.Application([
        ("/healthcheck", HealthCheckService, {"task": task}),
        ("/recent", StatusService, {"task": task}),
    ])


def parser(description="SEFT Publisher service."):
    here = os.path.dirname(__file__)
    p = argparse.ArgumentParser(description)
    p.add_argument(
        "--keys", default=os.path.abspath(os.path.join(here, "app/test")),
        help="Set a path to the keypair directory.")
    p.add_argument(
        "--port", type=int, default=int(os.getenv("SDX_SEFT_PUBLISHER_PORT", "8087")),
        help="Set a port for the service.")
    return p


def main(args):
    log.info("Launched in {0}.".format(os.getcwd()))

    services = json.loads(os.getenv("VCAP_SERVICES", "{}"))
    task = Task(args, services)

    # Create the API service
    app = make_app(task)
    app.listen(args.port)

    # Create the scheduled task
    transfer_ms = int(os.getenv("SEFT_FTP_INTERVAL_MS", DEFAULT_FTP_INTERVAL_MS))
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
