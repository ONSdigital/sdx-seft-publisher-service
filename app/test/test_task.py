import concurrent.futures
import multiprocessing
import time
import unittest

import tornado.concurrent
import tornado.ioloop

from app.test.localserver import serve
from app.test.test_ftp import NeedsTemporaryDirectory
from app.test.test_ftp import ServerTests
from main import Task


class TaskTests(NeedsTemporaryDirectory, unittest.TestCase):

    @staticmethod
    def stop_loop(future):
        loop = tornado.ioloop.IOLoop.current()
        loop.stop()

    def test_check_services(self):
        server = multiprocessing.Process(
            target=serve,
            args=(self.root,),
            kwargs=ServerTests.params
        )
        server.start()
        time.sleep(5)

        task = Task(None, {})
        self.assertIsNone(task.ftp_check)
        self.assertIsNone(task.rabbit_check)
        task.check_services(
            ftp_params=ServerTests.params,
            rabbit_url="https://pypi.python.org"
        )
        self.assertIsInstance(task.ftp_check, concurrent.futures.Future)
        self.assertIsInstance(task.rabbit_check, tornado.concurrent.Future)
        loop = tornado.ioloop.IOLoop.current()
        loop.add_future(task.rabbit_check, callback=self.stop_loop)
        loop.start()
        time.sleep(5)

        self.assertTrue(task.rabbit_check.done())
        self.assertTrue(task.rabbit_check.result())

        self.assertTrue(task.ftp_check.done())
        self.assertTrue(task.ftp_check.result())
        server.terminate()
