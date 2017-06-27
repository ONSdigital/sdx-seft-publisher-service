import io
import logging
import os

import aioftp
from aioftp.errors import StatusCodeError
import aiohttp
from aiohttp.client_exceptions import ClientConnectorError
import asyncio
from collections import Sequence
from sdx.common.logger_config import logger_initial_config
from shutil import copyfile
from structlog import wrap_logger
import uvloop

import settings


__version__ = "0.1.0"


logger_initial_config(service_name="sdx-seft-publisher-service")
logger = wrap_logger(logging.getLogger(__name__))


class PublishError(Exception):
    pass


class Publisher:

    def __init__(self, logger, host, port, login, password, ras_url, retrieved_file_types):
        self.logger = logger
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        self.loop = asyncio.get_event_loop()
        self.conn = aiohttp.TCPConnector(limit=0, limit_per_host=0)
        self.host = host
        self.port = port
        self.login = login
        self.password = password
        self.ras_url = ras_url
        self.retrieved_file_types = retrieved_file_types

    def post_data(self, session, fn, block, file_path):

        self.logger.info("Posting data to " + self.ras_url + fn)
        with aiohttp.MultipartWriter('form-data') as mpwriter:
            self.logger.info("testtest 1")
            headers={"CONTENT-TYPE": "formdata",
                     "CONTENT_ENCODING": "identity",
                     "CONTENT_TRANSFER_ENCODING": "binary"}
                                 payload["headers"] = headers
            mpwriter.append_payload(payload)
            mpwriter.parts[1].set_content_disposition(distype='formData', params=params)
            self.logger.info("testtest 2")
            headers = {"Content-Type": mpwriter.headers["CONTENT-TYPE"]}
            response = session.post(self.ras_url + fn, data=mpwriter, headers=headers)
            self.logger.info("testtest 3")
        return response

    async def publish_remove_files(self, path, ftp_client, http_session):
        if path.suffix in [self.retrieved_file_types]:
            resp = await self.publish(ftp_client, path, http_session)
            logger.info("testtest " + str(resp))
            if resp == 200:
                self.logger.info("File Published", file_path=path)
                self.logger.info("Deleting file from FTP", file_path=path)
                await ftp_client.remove_file(path)
                return None
            else:
                self.logger.error("Failed to publish file", file_path=path)
                raise PublishError

    async def publish(self, ftp_client, file_path, session):
        fn = os.path.basename(file_path)
        logger.info("Retrieving file from FTP", file_path=file_path)
        async with ftp_client.download_stream(file_path) as ftp_stream:
            async for block in ftp_stream.iter_by_block():
                async with self.post_data(session, fn, block, file_path) as resp:
                    return resp

    async def poll_ftp(self):
        client = aioftp.ClientSession(self.host, self.port, self.login, self.password)
        session = aiohttp.ClientSession(connector=self.conn)
        self.logger.info("Connecting to FTP")
        async with client as ftp_client:
            self.logger.info("Connecting to http session")
            async with session as http_session:
                self.logger.info("Getting file paths from FTP")
                for path, info in (await ftp_client.list(recursive=True)):
                    await self.publish_remove_files(path, ftp_client, http_session)

    def start(self):
        self.logger.info("Starting publisher")
        try:
            self.loop.run_until_complete(self.poll_ftp())
        except ConnectionRefusedError as e:
            self.logger.error("Could not connect to FTP. Closing loop", error=e)
            self.loop.stop()
        except StatusCodeError as e:
            self.logger.error("Failed FTP authentication. Closing loop", error=e)
            self.loop.stop()
        except ClientConnectorError as e:
            self.logger.error("Could not connect to RAS. Closing loop", error=e)
            self.loop.stop()
        except PublishError as e:
            self.logger.error("Some files have failed to publish", error=e)
            self.loop.stop()
        except Exception as e:
            self.logger.error("An Exception occurred", error=e)
            self.loop.stop()
        else:
            self.logger.info("All files transferred")


def get_default_publisher(logger):
    logger.info("Creating publisher")
    publisher = Publisher(logger,
                          settings.FTP_HOST,
                          settings.FTP_PORT,
                          settings.FTP_LOGIN,
                          settings.FTP_PASSWORD,
                          settings.RAS_URL,
                          settings.RETRIEVED_FILE_TYPES)
    return publisher


def main():
    logger.info("Start", version=__version__)
    publisher = get_default_publisher(logger)
    publisher.start()


if __name__ == "__main__":
    main()
