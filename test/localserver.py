import argparse
import logging
import sys

from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from pyftpdlib.authorizers import DummyAuthorizer


class MyHandler(FTPHandler):

    def on_connect(self):
        print "%s:%s connected" % (self.remote_ip, self.remote_port)

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

def serve(root):
    authorizer = DummyAuthorizer()
    authorizer.add_user('user', '12345', homedir=root, perm='elradfmw')
    authorizer.add_anonymous(homedir=root)

    handler = MyHandler
    handler.authorizer = authorizer
    server = FTPServer(('', 2121), handler)
    server.serve_forever()

def main(args):
    log = logging.getLogger("localftp")
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
    log = logging.getLogger("pyftpdlib")
    log.setLevel(args.log_level)
    log.addHandler(ch)

    work_dir = args.work if args.work and os.path.isdir(args.work) else tempfile.mkdtemp()
    return serve(work_dir)

def parser(description="FTP server for testing."):
    p = argparse.ArgumentParser(description)
    p.add_argument(
        "--work", default=None,
        help="Set a path to the working directory.")
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
