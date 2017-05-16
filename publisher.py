import ftplib
from ftplib import FTP
from multiprocessing import Pool
from io import  BytesIO
import os

import requests

s = requests.Session()

def retrieve_and_post(match):
    s = requests.Session()
    ftp = FTP()
    ftp.connect(host='127.0.0.1', port=2121)
    ftp.login(user='ons', passwd='ons')
    with BytesIO() as sf:
        s.post('http://0.0.0.0:8080/upload/bres/1/{}'.format(match), data=sf)
        ftp.retrbinary('RETR %s' %match, sf.write)
    ftp.close()


def main():
    pool = Pool(100)
    tasks = []
    ftp = FTP()
    ftp.connect(host='127.0.0.1', port=2121)
    ftp.login(user='ons', passwd='ons')
    files = (file for file in ftp.nlst() if '.xlsx' in os.path.splitext(file)[1])
    for file in files:
        tasks.append(pool.apply_async(retrieve_and_post, args=(file,)))

    for task in tasks:
        task.get()
    pool.close()
    pool.join()


if __name__ == "__main__":
    main()

