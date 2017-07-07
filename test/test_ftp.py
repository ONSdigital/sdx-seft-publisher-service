#!/usr/bin/env python3

import os
import multiprocessing
import shutil
import tempfile
import unittest

class NeedsTemporaryDirectory():

    def setUp(self):
        self.root = tempfile.mkdtemp()
        super().setUp()

    def tearDown(self):
        shutil.rmtree(self.root)


class ServerTests(NeedsTemporaryDirectory, unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.files = [tempfile.mkstemp(suffix=".xls", dir=self.root)] * 10
        print(self.files)
            
    @unittest.skipUnless(os.getenv("CF_INSTANCE_GUID"), "CF-only test")
    def test_cf_server(self):
        server = multiprocessing.Process(
            target=test.localserver.serve,
            args=(self.root,)
        )
        server.start()
        time.sleep(5)
        with zipfile.ZipFile(self.buf) as payload:
            for item in transfer(
                payload,
                host="0.0.0.0", port=22000,
                user="testuser", password="",
                root="test"
            ):
                print("transferred ", item)

        self.assertEqual(
            3,
            len(glob.glob(os.path.join(
                self.root, "data", "*",
            )))
        )
        self.assertEqual(
            4,
            len(glob.glob(os.path.join(
                self.root, "data", "sftpzip", "*"
            )))
        )
        self.assertEqual(
            2,
            len(glob.glob(os.path.join(
                self.root, "data", "sftpzip", "test", "*"
            )))
        )
        server.terminate()

    @unittest.skipIf(os.getenv("CF_INSTANCE_GUID"), "local-only test")
    def test_local_server(self):
        server = multiprocessing.Process(
            target=test.localserver.serve,
            args=(self.root,)
        )
        server.start()
        time.sleep(5)
        with zipfile.ZipFile(self.buf) as payload:
            for item in transfer(
                payload,
                host="0.0.0.0", port=22000,
                user="testuser", password="",
                root="test"
            ):
                print("transferred ", item)

        self.assertEqual(
            3,
            len(glob.glob(os.path.join(
                self.root, "data", "*", "sdx-spike", "*"
            )))
        )
        self.assertEqual(
            4,
            len(glob.glob(os.path.join(
                self.root, "data", "*", "sdx-spike", "sftpzip", "*"
            )))
        )
        self.assertEqual(
            2,
            len(glob.glob(os.path.join(
                self.root, "data", "*", "sdx-spike", "sftpzip", "test", "*"
            )))
        )
        server.terminate()

if __name__ == "__main__":
    unittest.main()
