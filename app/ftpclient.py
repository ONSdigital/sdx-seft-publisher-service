import datetime
from ftplib import FTP
from io import BytesIO
import logging
from os import path

from structlog import wrap_logger

from app.publisher import Job


# pylint: disable=broad-except
class FTPWorker:

    @staticmethod
    def get_wd(str_path):
        p = path.join(*str_path.split('\\'))
        return path.basename(path.normpath(p))

    def __init__(self, user, password, host, port, working_directory, timeout=30):
        self.logger = wrap_logger(logging.getLogger(__name__))
        self.user, self.password = user, password
        self.host, self.port = host, port
        self.timeout = timeout
        self.working_directory = self.get_wd(working_directory)
        self.ftp = FTP()

    def __enter__(self):
        try:
            self.ftp.connect(self.host, self.port, timeout=self.timeout)
        except Exception:
            self.logger.exception("Failed to connect to FTP server")
            return None

        try:
            self.ftp.login(user=self.user, passwd=self.password)
            self.ftp.cwd(self.working_directory)
        except Exception:
            self.logger.exception("Failed to login/cwd to FTP server")
            return None

        return self

    @property
    def filenames(self):
        """Gets list of filenames in directory using NLST"""
        try:
            return self.ftp.nlst()
        except Exception:
            self.logger.exception("Error getting filenames")
            return []

    def check(self):
        """Checks connection is alive using NOOP command"""
        with self as connected:
            try:
                connected.ftp.voidcmd("NOOP")
            except AttributeError:
                return False
            except Exception:
                self.logger.exception("Failed NOOP command")
                return False
            else:
                return True

    def get(self, filenames):
        """Gets files from FTP server using RETR command

        :param filenames:  List of filenames to retrieve from FTP server
        """
        while filenames:
            fp = filenames[0]
            buf = BytesIO()
            try:
                self.ftp.retrbinary("RETR {0}".format(fp), callback=buf.write)
            except Exception:
                self.logger.exception("Failed to get file")
            else:
                yield Job(datetime.datetime.utcnow(), fp, buf.getvalue())
                filenames.remove(fp)

    def delete(self, filename):
        """Deletes file from FTP server

        :param filename:  The name of the file to be deleted
        """
        try:
            self.ftp.delete(filename)
            return True
        except Exception:
            self.logger.exception("Failed to delete file")
            return False

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.ftp.quit()
        except Exception:
            self.logger.exception("Error during connection closure")
        return False
