#!/usr/bin/env python3
#   encoding: UTF-8

import argparse
import logging
from logging.handlers import WatchedFileHandler
import os.path
import tempfile
import sys

from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from pyftpdlib.authorizers import DummyAuthorizer


class MyHandler(FTPHandler):

    def on_connect(self):
        print("{0}:{1} connected".format(self.remote_ip, self.remote_port))

    def on_disconnect(self):
        # do something when client disconnects
        pass

    def on_login(self, username):
        # do something when user login
        pass

    def on_logout(self, username):
        # do something when user logs out
        pass

    def on_file_sent(self, file):
        # do something when a file has been sent
        pass

    def on_file_received(self, file):
        # do something when a file has been received
        pass

    def on_incomplete_file_sent(self, file):
        # do something when a file is partially sent
        pass

    def on_incomplete_file_received(self, file):
        # remove partially uploaded files
        import os
        os.remove(file)


def serve(root, user, password, host, port, working_directory):
    authorizer = DummyAuthorizer()
    authorizer.add_user(user, password, homedir=root, perm="elradfmw")
    authorizer.add_anonymous(homedir=root)

    handler = MyHandler
    handler.authorizer = authorizer
    server = FTPServer((host, port), handler)
    server.serve_forever()


def main(args):
    logger = logging.getLogger("localftp")
    logger.setLevel(args.log_level)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s|%(message)s")
    ch = logging.StreamHandler()

    if args.log_path is None:
        ch.setLevel(args.log_level)
    else:
        fh = WatchedFileHandler(args.log_path)
        fh.setLevel(args.log_level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        ch.setLevel(logging.WARNING)

    ch.setFormatter(formatter)
    logger.addHandler(ch)
    log = logging.getLogger("pyftpdlib")
    logger.setLevel(args.log_level)
    logger.addHandler(ch)

    work_dir = args.work if args.work and os.path.isdir(args.work) else tempfile.mkdtemp()
    return serve(work_dir, "testuser", "password", "127.0.0.1", args.port)


def parser(description="FTP server for testing."):
    p = argparse.ArgumentParser(description)
    p.add_argument(
        "--work", default=None,
        help="Set a path to the working directory.")
    p.add_argument(
        "--port", type=int, default=21,
        help="Set a port for the service.")
    p.add_argument(
        "-v", "--verbose", required=False,
        action="store_const", dest="log_level",
        const=logging.DEBUG, default=logging.INFO,
        help="Increase the verbosity of output")
    p.add_argument(
        "--log", default=None, dest="log_path",
        help="Set a file path for log output")
    return p

if __name__ == "__main__":
    p = parser()
    args = p.parse_args()
    rv = main(args)
    sys.exit(rv)
