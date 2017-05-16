#!/usr/bin/env python
#coding: UTF-8
import asyncio
from datetime import datetime as dt
import os

import aioftp
import aiohttp
from aiohttp import StreamReader
from structlog.processors import JSONRenderer, TimeStamper
import uvloop

import settings

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
loop = asyncio.get_event_loop()

conn = aiohttp.TCPConnector(limit=0, limit_per_host=0)


async def publish(ftp_client, file_path, session):
    fn = os.path.basename(file_path)
    async with ftp_client.download_stream(file_path) as ftp_stream:
        async for block in ftp_stream.iter_by_block():
            async with session.post("http://localhost:8080/upload/bres/1/" + fn,
                                data=block) as resp:
                return resp.status


async def poll_ftp(host, port, login, password):
    async with aioftp.ClientSession(host, port, login, password) as ftp_client:
        async with aiohttp.ClientSession(connector=conn) as http_session:
            for path, info in (await ftp_client.list(recursive=False)):
                #if info["type"] == "file" and 'book1.xlsx' in str(path):
                if info["type"] == "file" and path.suffix == ".xlsx":
                    # stream = StreamReader()
                    # await stream_file(ftp_client, path, stream)
                    resp = await publish(ftp_client, path, http_session)

                    if resp == 200:
                        await ftp_client.remove_file(path)


def main():
    loop.run_until_complete(poll_ftp("127.0.0.1", 2121, "ons", "ons"))

if __name__ == "__main__":
    main()
