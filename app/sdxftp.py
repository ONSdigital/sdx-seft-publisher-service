from io import BytesIO

from ftplib import FTP, Error


class SDXFTP(object):

    def __init__(self, logger, host, user, passwd, port=21):
        self._conn = None
        self.host = host
        self.user = user
        self.password = passwd
        self.logger = logger
        self.port = port
        return

    def get_connection(self):
        """Connect checks whether an ftp connection is already open and, if
        not, attempts to open a new one.
        """
        if self._conn is None:
            # No connection at all
            self.logger.info("Establishing new FTP connection", host=self.host)
            return self._connect()
        else:
            try:
                self._conn.voidcmd("NOOP")
            except (IOError, AttributeError):
                # Bad response so assume connection is dead and attempt
                # to reopen.
                self.logger.info("FTP connection no longer alive, re-establishing connection", host=self.host)
                return self._connect()

            # Connection exists and seems healthy
            self.logger.info("FTP connection already established", host=self.host)
            return self._conn

    def _connect(self):
        self._conn = FTP()
        self._conn.connect(self.host, self.port)
        self._conn.login(user=self.user, passwd=self.password)
        return self._conn

    def read_directory(self):
        '''
            :return: a list of files 
        '''
        try:
            conn = self.get_connection()
            return conn.nlst()
        except (ConnectionRefusedError, Error) as e:
            self.logger.exception(e)
            return []

    def read_file(self, file):
        '''
            :return the bytes of the file
        '''
        try:
            conn = self.get_connection()
            bytes_buffer = BytesIO()
            self.logger.info("Retrieving file {0}".format(file))
            conn.retrbinary("RETR {}".format(file), callback=bytes_buffer.write)
            self.logger.info("File retrieved")
            return bytes_buffer.getvalue()
        except Error as e:
            self.logger.exception(e)
            self.logger.error("Unable to read file")
            return None

    def delete_file(self, file):
        try:
            conn = self.get_connection()
            conn.delete(file)
        except (ConnectionRefusedError, Error) as e:
            self.logger.exception(e)
            self.logger.error("Unable to delete file")

