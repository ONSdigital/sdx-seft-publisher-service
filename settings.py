import logging
import os


LOGGING_LEVEL = logging.getLevelName(os.getenv('LOGGING_LEVEL', 'INFO'))

FTP_HOST = os.getenv('FTP_HOST', "127.0.0.1")
FTP_PORT = os.getenv('FTP_PORT', 2123)
FTP_LOGIN = os.getenv('FTP_LOGIN', "ons")
FTP_PASSWORD = os.getenv('FTP_PASSWORD', "ons")

RAS_URL = os.getenv('RAS_URL', "http://localhost:8080/upload/bres/1/")

RETRIEVED_FILE_TYPES = os.getenv('RETRIEVED_FILE_TYPES', '.xlsx')
