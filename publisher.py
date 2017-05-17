#!/usr/bin/env python
import ftplib
from ftplib import FTP
from io import BytesIO
import logging
from multiprocessing import Pool
import os

import requests

import settings

logging.basicConfig(level=settings.LOGGING_LEVEL,
                    format=settings.LOGGING_FORMAT)

s = requests.Session()

def conn():
    try:
        ftp = FTP()
        ftp.connect(host='127.0.0.1', port=2121)
        ftp.login(user='ons', passwd='ons')
        return ftp
    except (ftplib.all_errors, ConnectionRefusedError) as e:
        logging.error("Could not connect to ftp",
                     host=host,
                     port=port)


def retrieve_and_post(match):
    ftp = conn()

    binary_stream = BytesIO()
    ftp.retrbinary('RETR %s' %match, binary_stream.write)
    binary_stream.seek(0)

    r = upload(binary_stream, match)

    if r.status_code == 200:
        ftp.delete(match)
    ftp.close()


def upload(binary_file, file_name):
    headers = headers={'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}
    r = s.post('http://0.0.0.0:8080/upload/bres/1/{}'.format(file_name),
                      files={'file': binary_file.getvalue()})
    binary_file.close()
    return r


def run():
    pool = Pool(8)
    tasks = []
    ftp = con()
    files = (file for file in ftp.nlst() if '.xlsx' in os.path.splitext(file)[1])
    for file in files:
        tasks.append(pool.apply_async(retrieve_and_post, args=(file,)))

    for task in tasks:
        task.get()

    pool.close()
    pool.join()


if __name__ == "__main__":
    run()

