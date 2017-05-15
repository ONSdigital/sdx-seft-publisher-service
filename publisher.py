#!/usr/bin/env python
#coding: UTF-8
import asyncio
from datetime import datetime as dt
import logging
import os

import aioftp
import aiohttp
from aiohttp import StreamReader
from structlog import wrap_logger
from structlog.processors import JSONRenderer, TimeStamper
import uvloop

import settings

def _add_timestamp(_, __, event_dict):
    event_dict['timestamp'] = dt.utcnow()
    return event_dict

logging.basicConfig(level=settings.LOGGING_LEVEL,
                    format=settings.LOGGING_FORMAT)

logger = wrap_logger(logging.getLogger(__name__),
                     processors=[_add_timestamp,
                                TimeStamper(fmt='iso'),
                                JSONRenderer(indent=1, sort_keys=True)])

logging.getLogger('aioftp.client').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.get_event_loop()

conn = aiohttp.TCPConnector(limit=0, limit_per_host=0)


async def publish(ftp_client, file_path, session):
    fn = os.path.basename(str(file_path))
    logger.info("POSTing {}".format(fn))
    async with ftp_client.download_stream(file_path) as ftp_stream:
        async for block in ftp_stream.iter_by_block():
            async with session.post("http://localhost:8080/upload/bres/1/" + fn,
                                data=block) as resp:
                return resp.status


async def poll_ftp(host, port, login, password):
    async with aioftp.ClientSession(host, port, login, password) as ftp_client:
        async with aiohttp.ClientSession(connector=conn) as http_session:
            logger.info("parsing directory")
            for path, info in (await ftp_client.list(recursive=False)):
                # if info["type"] == "file" and 'book1.xlsx' in str(path):
                if info["type"] == "file" and path.suffix == ".xlsx":
                    stream = StreamReader()
                    logger.info("streaming file")
                    # await stream_file(ftp_client, path, stream)
                    resp = await publish(ftp_client, path, http_session)

                    if resp == 200:
                        logger.info("deleting {}".format(path))
                        await ftp_client.remove_file(path)


def main():
    loop.run_until_complete(poll_ftp("127.0.0.1", 2121, "ons", "ons"))

if __name__ == "__main__":
    logger.info("starting publisher")
    main()
