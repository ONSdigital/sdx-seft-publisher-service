import concurrent.futures
import multiprocessing
import time
import unittest

import tornado.concurrent

from app.main import Task
from app.test.localserver import serve
from app.test.test_ftp import NeedsTemporaryDirectory
from app.test.test_ftp import ServerTests


class TaskTests(NeedsTemporaryDirectory, unittest.TestCase):

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
        task.check_services(ServerTests.params)
        self.assertIsInstance(task.ftp_check, concurrent.futures.Future)
        self.assertIsInstance(task.rabbit_check, tornado.concurrent.Future)
        time.sleep(5)

        self.assertTrue(task.ftp_check.done())
        self.assertTrue(task.ftp_check.result())
        server.terminate()
