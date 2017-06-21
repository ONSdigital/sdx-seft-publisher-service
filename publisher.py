import asyncio
import logging
import os

import aioftp
from aioftp.errors import StatusCodeError
import aiohttp
from aiohttp.client_exceptions import ClientConnectorError
from aiohttp import StreamReader
from sdx.common.logger_config import logger_initial_config
from structlog import wrap_logger
import uvloop

import settings


class Publisher:

    def __init__(self, logger, host, port, login, password, ras_url):
        self.logger = logger
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        self.loop = asyncio.get_event_loop()
        self.conn = aiohttp.TCPConnector(limit=0, limit_per_host=0)
        self.host = host
        self.port = port
        self.login = login
        self.password = password
        self.ras_url = ras_url

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
        client = aioftp.ClientSession(self.host, self.port, self.login, self.password)
        async with client as ftp_client:
            self.logger.info("Connecting to http_session")
            session = aiohttp.ClientSession(connector=self.conn)
            async with session as http_session:
                failed = []
                for path, info in (await ftp_client.list(recursive=True)):
                    if path.suffix == ".xlsx":
                        resp = await self.publish(ftp_client, path, http_session)
                        if resp == 200:
                            await ftp_client.remove_file(path)
                        else:
                            failed.append(path)
                if len(failed) > 0:
                    self.logger.error("Some files were not transferred.", files=failed)

    def start(self):
        self.logger.info("Starting publisher")
        try:
            self.loop.run_until_complete(self.poll_ftp())
        except ConnectionRefusedError as e:
            self.logger.error("Could not connect to FTP. Closing loop.", error=e)
            self.loop.stop()
        except StatusCodeError as e:
            self.logger.error("Failed FTP authentication. Closing loop.", error=e)
            self.loop.stop()
        except ClientConnectorError as e:
            self.logger.error("Could not connect to RAS. Closing loop.", error=e)
            self.loop.stop()
        else:
            self.logger.info("All files transferred")


def main():
    logger_initial_config(service_name="sdx-seft-publisher-service")
    logger = wrap_logger(logging.getLogger(__name__))

    publisher = Publisher(logger,
                          settings.FTP_HOST,
                          settings.FTP_PORT,
                          settings.FTP_LOGIN,
                          settings.FTP_PASSWORD,
                          settings.RAS_URL)
    publisher.start()


if __name__ == "__main__":
    main()
