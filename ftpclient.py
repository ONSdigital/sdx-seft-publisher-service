import datetime
from ftplib import FTP
from io import BytesIO
import logging

from publisher import Job

class FTPWorker:

    def __init__(self, user, password, host, port, timeout=30, **kwargs):
        self.log = logging.getLogger("sdx.FTPWorker")
        self.user, self.password = user, password
        self.host, self.port = host, port
        self.timeout = timeout
        self.ftp = FTP()

    def __enter__(self):
        try:
            self.ftp.connect(self.host, self.port, timeout=self.timeout)
        except Exception as e:
            log.warning(e)
            return None

        try:
            self.ftp.login(user=self.user, passwd=self.password)
        except Exception as e:
            self.log.warning(e)
            return None

        return self

    @property
    def filenames(self):
        try:
            return self.ftp.nlst()
        except Exception as e:
            self.log.warning(e)
            return []

    def get(self, filenames):
        while filenames:
            fp = filenames[0]
            buf = BytesIO()
            try:
                self.ftp.retrbinary("RETR {0}".format(fp), callback=buf.write)
            except Exception as e:
                self.log.warning(e)
            else:
                yield Job(datetime.datetime.utcnow(), fp, buf.getvalue())
                filenames.remove(fp)

    def delete(self, filename):
        try:
            self.ftp.delete(filename)
            return True
        except Exception as e:
            self.log.warning(e)
            return False

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.ftp.quit()
        except Exception as e:
            self.log.warning(e)
        return False
