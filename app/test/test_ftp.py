#!/usr/bin/env python3
#   encoding: UTF-8

import os
import multiprocessing
import random
import shutil
import sys
import tempfile
import time
import unittest
import unittest.mock

# To run test in CF
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ftpclient import FTPWorker

try:
    from localserver import serve
except ImportError:
    # Travis CI
    from app.test.localserver import serve


class NeedsTemporaryDirectory():

    def setUp(self):
        self.root = tempfile.mkdtemp()
        super().setUp()

    def tearDown(self):
        shutil.rmtree(self.root)


class ExceptionTests(unittest.TestCase):

    params = {
        "user": "testuser",
        "password": "password",
        "host": "0.0.0.0",
        "port": 2121,
        "working_directory": ".",
    }

    @unittest.mock.patch("ftpclient.FTP.connect", side_effect=Exception("Connect failure"))
    def test_error_on_connect(self, connect_mock):
        worker = FTPWorker(**self.params)
        with worker as broker:
            self.assertFalse(broker)
            connect_mock.assert_called_once()

    @unittest.mock.patch("ftpclient.FTP.connect")
    @unittest.mock.patch("ftpclient.FTP.login", side_effect=Exception("Login failure"))
    def test_error_on_login(self, connect_mock, login_mock):
        worker = FTPWorker(**self.params)
        with worker as broker:
            self.assertFalse(broker)
            login_mock.assert_called_once()


class ServerTests(NeedsTemporaryDirectory, unittest.TestCase):

    params = {
        "user": "testuser",
        "password": "password",
        "host": "0.0.0.0",
        "port": 2121,
        "working_directory": ".",
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
            target=serve,
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
            target=serve,
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
            target=serve,
            args=(self.root,),
            kwargs=self.params
        )
        server.start()
        time.sleep(5)
        worker = FTPWorker(**self.params)
        with worker as active:
            items = set(i.file for i in active.get(active.filenames))
            self.assertEqual(len(self.files), len(items))
            self.assertEqual(set(self.files.values()), items)

        server.terminate()

    @unittest.skipIf(os.getenv("CF_INSTANCE_GUID"), "local-only test")
    def test_local_server_get(self):
        server = multiprocessing.Process(
            target=serve,
            args=(self.root,),
            kwargs=self.params
        )
        server.start()
        time.sleep(5)
        worker = FTPWorker(**self.params)
        with worker as active:
            items = set(i.file for i in active.get(active.filenames))
            self.assertEqual(len(self.files), len(items))
            self.assertEqual(set(self.files.values()), items)

        server.terminate()

    def test_path_names(self):
        paths = [
            '\\\\EDC_Templates',
            '\\\\EDC_Templates\\',
            '\\EDC_Templates',
            '/EDC_Templates/',
            'EDC_Templates',
        ]

        [self.assertEqual(FTPWorker.get_wd(path), 'EDC_Templates') for path in paths]

if __name__ == "__main__":
    unittest.main()
