#!/usr/bin/env python3

import os
import multiprocessing
import random
import shutil
import sys
import tempfile
import time
import unittest

# To run test in CF
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from app.ftpclient import FTPWorker
import app.test.localserver

"""
To run this test in a Cloudfoundry environment:

$ cf push seft-publisher
$ cf logs seft-publisher --recent

"""


class NeedsTemporaryDirectory():

    def setUp(self):
        self.root = tempfile.mkdtemp()
        super().setUp()

    def tearDown(self):
        shutil.rmtree(self.root)


class ServerTests(NeedsTemporaryDirectory, unittest.TestCase):

    params = {
        "user": "testuser",
        "password": "password",
        "host": "0.0.0.0",
        "port": 2121,
    }

    def setUp(self):
        super().setUp()
        self.files = {
            tempfile.mkstemp(
                suffix=".xls", dir=self.root
            ): os.urandom(random.randint(1024, 4049))
            for i in range(12)
        }
        for (fd, path), content in self.files.items():
            os.write(fd, content)
            os.close(fd)

    @unittest.skipUnless(os.getenv("CF_INSTANCE_GUID"), "CF-only test")
    def test_cf_server_delete(self):
        server = multiprocessing.Process(
            target=app.test.localserver.serve,
            args=(self.root,),
            kwargs=self.params
        )
        server.start()
        time.sleep(5)
        worker = FTPWorker(**self.params)
        with worker as active:
            n = len(self.files)
            for fn in active.filenames:
                with self.subTest(fn=fn):
                    self.assertTrue(active.delete(fn))
                    n -= 1
                    self.assertEqual(n, len(os.listdir(self.root)))

        server.terminate()

    @unittest.skipIf(os.getenv("CF_INSTANCE_GUID"), "local-only test")
    def test_local_server_delete(self):
        server = multiprocessing.Process(
            target=app.test.localserver.serve,
            args=(self.root,),
            kwargs=self.params
        )
        server.start()
        time.sleep(5)
        worker = FTPWorker(**self.params)
        with worker as active:
            n = len(self.files)
            for fn in active.filenames:
                with self.subTest(fn=fn):
                    self.assertTrue(active.delete(fn))
                    n -= 1
                    self.assertEqual(n, len(os.listdir(self.root)))

        server.terminate()

    @unittest.skipUnless(os.getenv("CF_INSTANCE_GUID"), "CF-only test")
    def test_cf_server_get(self):
        server = multiprocessing.Process(
            target=app.test.localserver.serve,
            args=(self.root,),
            kwargs=self.params
        )
        server.start()
        time.sleep(5)
        worker = FTPWorker(**self.params)
        with worker as active:
            items = set(i.contents for i in active.get(active.filenames))
            self.assertEqual(len(self.files), len(items))
            self.assertEqual(set(self.files.values()), items)

        server.terminate()

    @unittest.skipIf(os.getenv("CF_INSTANCE_GUID"), "local-only test")
    def test_local_server_get(self):
        server = multiprocessing.Process(
            target=app.test.localserver.serve,
            args=(self.root,),
            kwargs=self.params
        )
        server.start()
        time.sleep(5)
        worker = FTPWorker(**self.params)
        with worker as active:
            items = set(i.contents for i in active.get(active.filenames))
            self.assertEqual(len(self.files), len(items))
            self.assertEqual(set(self.files.values()), items)

        server.terminate()

if __name__ == "__main__":
    unittest.main()
