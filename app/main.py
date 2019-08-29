#!/usr/bin/env python3

import argparse
import base64
import json
import os.path
import sys
import tornado.ioloop
import tornado.web
import uuid
import yaml

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from tornado.httpclient import AsyncHTTPClient, HTTPError
from sdc.crypto.encrypter import encrypt
from sdc.crypto.key_store import KeyStore, validate_required_keys

from app import create_and_wrap_logger
from app.ftpclient import FTPWorker
from app.publisher import DurableTopicPublisher

DEFAULT_FTP_INTERVAL_MS = 10 * 60 * 1000  # 10 minutes

logger = create_and_wrap_logger(__name__)


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

        ftp_health = self.task.ftp_check.done() and self.task.ftp_check.result()

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
        self.key_purpose = 'outbound'

        keys_file_location = os.getenv('SDX_KEYS_FILE', './jwt-test-keys/keys.yml')
        with open(keys_file_location) as file:
            self.secrets_from_file = yaml.safe_load(file)

        validate_required_keys(self.secrets_from_file, self.key_purpose)
        self.key_store = KeyStore(self.secrets_from_file)

    def check_services(self, ftp_params=None, rabbit_url=""):
        ftp_params = ftp_params or self.ftp_params(self.services)
        http_client = AsyncHTTPClient()
        params = self.amqp_params(self.services)
        self.rabbit_check = http_client.fetch(rabbit_url or params["check"])

        ftp = FTPWorker(**ftp_params)
        self.ftp_check = self.executor.submit(ftp.check)

    def transfer_files(self):
        if not self.publisher.publishing:
            logger.warning("Publisher is not ready.")
            return

        if self.transfer:
            logger.warning("Cancelling overlapped task.")
            return
        else:
            self.transfer = True

        try:
            logger.info("Looking for files...")
            worker = FTPWorker(**self.ftp_params(self.services))
            with worker as active:
                if not active:
                    return

                for job in active.get(active.filenames):
                    if job.filename not in self.recent:
                        logger.info("Found a file to publish", filename=job.filename)
                        data = job._asdict()
                        data["file"] = base64.standard_b64encode(job.file).decode("ascii")
                        data["ts"] = job.ts.isoformat()
                        payload = encrypt(data, self.key_store, self.key_purpose)
                        tx_id = str(uuid.uuid4())

                        msg_id = self.publisher.publish_message(payload, headers={'tx_id': tx_id})
                        if msg_id is None:
                            logger.warning("Failed to publish file", filename=job.filename)
                        else:
                            self.recent[job.filename] = msg_id
                            logger.info("Published file", filename=job.filename, tx_id=tx_id)

                logger.info("Finished publishing files, checking if any files need to be deleted")
                for filename, msg_id in self.recent.items():
                    logger.info("Recently published file found", filename=filename, msg_id=msg_id)
                    # The file might not be in confirmed_deliveries as the publisher waits for the delivery
                    # confirmation adding it to the list
                    if msg_id in self.publisher.confirmed_deliveries:
                        logger.info("Deleting file as it has its delivery confirmed",
                                    filename=filename, msg_id=msg_id)
                        file_deleted = active.delete(filename)
                        if file_deleted:
                            del self.recent[filename]
                            logger.info("Succssfully deleted file", filename=filename, msg_id=msg_id)
                    else:
                        logger.info("Not deleting file as it hasn't had its delivery confirmed",
                                    filename=filename, msg_id=msg_id)
        finally:
            self.transfer = False
            logger.info("Finished looking for files.")


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
    logger.info("Application launched", cwd=os.getcwd())

    services = json.loads(os.getenv("VCAP_SERVICES", "{}"))
    task = Task(args, services)

    # Create the API service
    app = make_app(task)
    app.listen(args.port)

    # Create the scheduled task
    transfer_ms = int(os.getenv("SEFT_FTP_INTERVAL_MS", DEFAULT_FTP_INTERVAL_MS))
    transfer = tornado.ioloop.PeriodicCallback(task.transfer_files, transfer_ms)
    transfer.start()
    logger.info("Transfer scheduled.")

    check_ms = 5 * 60 * 1000  # 5 minutes
    check = tornado.ioloop.PeriodicCallback(
        task.check_services,
        check_ms,
    )
    check.start()
    logger.info("Check scheduled.")

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
