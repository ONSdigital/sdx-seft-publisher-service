import datetime
from ftplib import FTP
from io import BytesIO
import logging
from os import path

from app.publisher import Job


class FTPWorker:

    @staticmethod
    def get_wd(str_path):
        p = path.join(*str_path.split('\\'))
        return path.basename(path.normpath(p))

    def __init__(self, user, password, host, port, working_directory, timeout=30):
        self.log = logging.getLogger("sdx.FTPWorker")
        self.user, self.password = user, password
        self.host, self.port = host, port
        self.timeout = timeout
        self.working_directory = self.get_wd(working_directory)
        self.ftp = FTP()

    def __enter__(self):
        try:
            self.ftp.connect(self.host, self.port, timeout=self.timeout)
        except Exception as e:
            self.log.warning(e)
            return None

        try:
            self.ftp.login(user=self.user, passwd=self.password)
            self.ftp.cwd(self.working_directory)
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

    def getfile(self, filename):

        buf = BytesIO()
        try:
            self.ftp.retrbinary("RETR {0}".format(filename), callback=buf.write)
            return Job(datetime.datetime.utcnow(), filename, buf.getvalue())
        except Exception as e:
            self.log.warning(e)
            return None



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
