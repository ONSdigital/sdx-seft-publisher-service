import unittest

import aiohttp
from aiohttp.client_exceptions import ClientConnectorError
import asynctest

from publisher import get_default_publisher
from publisher import logger
from publisher import PublishError


class TestPublisher(unittest.TestCase):

    def setUp(self):
        self.logger = logger
        self.pub = get_default_publisher(logger)

    async def test_delete_if_sent(self):
        path = 'test.xlsx'
        pub_rem = getattr(self.pub, 'publish_remove_files')
        with asynctest.mock.patch("publisher.Publisher.publish") as mock_publish:
            mock_publish.return_value = 200
            mock_ftp = asynctest.mock.Mock()
            await pub_rem(path, ftp_client=mock_ftp, http_session=None)
            mock_ftp.remove_file.assert_called_with()

    async def test_not_delete_if_not_sent(self):
        path = 'test.xlsx'
        pub_rem = getattr(self.pub, 'publish_remove_files')
        with asynctest.mock.patch("publisher.Publisher.publish") as mock_publish:
            mock_publish.return_value = 400
            mock_ftp = asynctest.mock.Mock()
            await pub_rem(path, ftp_client=mock_ftp, http_session=None)
            mock_ftp.remove_file.assert_not_called()
            self.assertRaises(PublishError)

    async def test_publish_xlsx(self):
        path = 'test.xlsx'
        pub_rem = getattr(self.pub, 'publish_remove_files')
        with asynctest.mock.patch("publisher.Publisher.publish") as mock_publish:
            mock_ftp = asynctest.mock.Mock()
            await pub_rem(path, ftp_client=mock_ftp, http_session=None)
            mock_publish.assert_called_with()

    async def test_not_publish_xlsx(self):
        path = 'test.png'
        pub_rem = getattr(self.pub, 'publish_remove_files')
        with asynctest.mock.patch("publisher.Publisher.publish") as mock_publish:
            mock_ftp = asynctest.mock.Mock()
            await pub_rem(path, ftp_client=mock_ftp, http_session=None)
            mock_publish.assert_not_called()

    def test_ftp_connect_failure(self):
        self.pub.start()
        self.assertRaises(ConnectionRefusedError)

    def test_ras_connect_failure(self):
        conn = aiohttp.TCPConnector(limit=0, limit_per_host=0)
        session = aiohttp.ClientSession(connector=conn)
        block = {"data": "data"}
        post_data = getattr(self.pub, 'post_data')
        post_data(session=session, fn='fn', block=block)
        self.assertRaises(ClientConnectorError)
