import asyncio
import os
import logging

import aioftp
import aiohttp
from aiohttp.client_exceptions import ClientConnectorError
from aiohttp import StreamReader
from structlog import wrap_logger
import uvloop

import settings


logging.basicConfig(level=settings.LOGGING_LEVEL,
                    format=settings.LOGGING_FORMAT,
                    datefmt=settings.DATE_FORMAT)
logger = wrap_logger(logging.getLogger(__name__))


class Publisher:

    def __init__(self, host, port, login, password):
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        self.loop = asyncio.get_event_loop()
        self.conn = aiohttp.TCPConnector(limit=0, limit_per_host=0)
        self.host = host
        self.port = port
        self.login = login
        self.password = password

    def get_ftp_client(self):
        try:
            client = aioftp.ClientSession(self.host, self.port, self.login, self.password)
            return client
        except ConnectionRefusedError as e:
            logger.error("Could not connect to ftp server",
                         host=self.host,
                         port=self.port,
                         error=e)

    def post_data(self, session, fn, block):
        try:
            response = session.post("http://localhost:8080/upload/bres/1/" + fn, data=block)
            return response
        except ConnectionRefusedError as e:
            logger.error("Could not connect to RAS service", error=e)
        except ClientConnectorError as e:
            logger.error("Could not connect to RAS service", error=e)

    async def publish(self, ftp_client, file_path, session):
        fn = os.path.basename(file_path)
        async with ftp_client.download_stream(file_path) as ftp_stream:
            async for block in ftp_stream.iter_by_block():
                async with self.post_data(session, fn, block) as resp:
                    return resp.status

    async def poll_ftp(self):
        async with self.get_ftp_client() as ftp_client:
            async with aiohttp.ClientSession(connector=self.conn) as http_session:
                for path, info in (await ftp_client.list(recursive=True)):
                    if info["type"] == "file" and path.suffix == ".xlsx":
                        resp = await self.publish(ftp_client, path, http_session)
                        if resp == 200:
                            await ftp_client.remove_file(path)

    def start(self):
        self.loop.run_until_complete(self.poll_ftp())


def main():
    publisher = Publisher("127.0.0.1", 2122, "ons", "ons")
    publisher.start()


if __name__ == "__main__":
    main()
