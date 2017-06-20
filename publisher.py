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

    def __init__(self, logger, host, port, login, password):
        self.logger = logger
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        self.loop = asyncio.get_event_loop()
        self.conn = aiohttp.TCPConnector(limit=0, limit_per_host=0)
        self.host = host
        self.port = port
        self.login = login
        self.password = password
        self.ras_url = settings.RAS_URL

    def get_ftp_client(self):
        client = aioftp.ClientSession(self.host, self.port, self.login, self.password)
        return client

    def post_data(self, session, fn, block):
        self.logger.info("Posting data to " + self.ras_url + fn)
        response = session.post(self.ras_url + fn, data=block)
        self.logger.info("File sent to RAS")
        return response

    async def publish(self, ftp_client, file_path, session):
        self.logger.info("Publishing all messages from ftp")
        fn = os.path.basename(file_path)
        async with ftp_client.download_stream(file_path) as ftp_stream:
            async for block in ftp_stream.iter_by_block():
                async with self.post_data(session, fn, block) as resp:
                    return resp.status

    async def poll_ftp(self):
        self.logger.info("Connecting to FTP")
        async with self.get_ftp_client() as ftp_client:
            self.logger.info("Connecting to http_session")
            async with aiohttp.ClientSession(connector=self.conn) as http_session:
                for path, info in (await ftp_client.list(recursive=True)):
                    if path.suffix == ".xlsx":
                        resp = await self.publish(ftp_client, path, http_session)
                        failed = []
                        if resp == 200:
                            await ftp_client.remove_file(path)
                        else:
                            failed.append(path)

    def start(self):
        self.logger.info("Starting publisher")
        try:
            self.loop.run_until_complete(self.poll_ftp())
        except ConnectionRefusedError as e:
            self.logger.error("A connection has failed", error=e)
            self.loop.stop()
        except ClientConnectorError as e:
            self.logger.error("A connection has failed", error=e)
            self.loop.stop()
        finally:
            self.logger.info("All files transferred")


def main():
    publisher = Publisher(logger, "127.0.0.1", 2122, "ons", "ons")
    publisher.start()


if __name__ == "__main__":
    main()