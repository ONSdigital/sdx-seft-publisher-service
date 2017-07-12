import argparse
from collections import deque
import logging
from logging.handlers import WatchedFileHandler
import sys

import tornado.ioloop
import tornado.web

from ftpclient import FTPWorker


class StatusService(tornado.web.RequestHandler):

    def initialize(self, work):
        self.recent = {n: v._asdict() for n, v in enumerate(Work.recent)}

    def get(self):
        self.write(self.recent)


class Work:
    recent = deque(maxlen=24)

    @staticmethod
    def params(settings):
        return {
            "user": "testuser",
            "password": "password",
            "host": "0.0.0.0",
            "port": 2121,
        }

    @classmethod
    def transfer_task(cls):
        log = logging.getLogger("sdx.seft")
        log.info("Looking for files...")
        worker = FTPWorker(**cls.params(None))
        # publisher = ?
        with worker as active:
            for job in active.get(active.filenames):
                while True:
                    payload = encrypt(job.contents)
                    if not publisher.publish(payload):
                        continue

                while True:
                    if not active.delete(job.fn):
                        continue

                cls.recent.append((job.ts.isoformat(), job.fn))


def make_app():
    return tornado.web.Application([
        (r"/recent", StatusService, {"work": Work}),
    ])


def parser(description="SEFT Publisher service."):
    p = argparse.ArgumentParser(description)
    p.add_argument(
        "-v", "--verbose", required=False,
        action="store_const", dest="log_level",
        const=logging.DEBUG, default=logging.INFO,
        help="Increase the verbosity of output")
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

    # Create the API service
    app = make_app()
    app.listen(8888)

    # Create the scheduled task
    interval_ms = 30 * 60 * 1000
    sched = tornado.ioloop.PeriodicCallback(
        Work.transfer_task,
        interval_ms,
    )

    sched.start()
    log.info("Scheduler started.")

    # Perform the first transfer immediately
    loop = tornado.ioloop.IOLoop.current()
    loop.spawn_callback(Work.transfer_task)
    loop.start()
    return 0

if __name__ == "__main__":
    p = parser()
    args = p.parse_args()
    rv = main(args)
    sys.exit(rv)
