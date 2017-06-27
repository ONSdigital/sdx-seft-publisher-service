import logging
import os


LOGGING_LEVEL = logging.getLevelName(os.getenv('LOGGING_LEVEL', 'INFO'))

FTP_HOST = os.getenv('FTP_HOST', "127.0.0.1")
FTP_PORT = os.getenv('FTP_PORT', 2123)
FTP_LOGIN = os.getenv('FTP_LOGIN', "ons")
FTP_PASSWORD = os.getenv('FTP_PASSWORD', "ons")

RAS_URL = os.getenv('RAS_URL',
                    # "http://localhost:8080/upload/dd/dd/")
                    "https://api-dev.apps.mvp.onsclofo.uk:443/collection-instrument-api/1.0.2/ui/upload/0282bdf5-51a0-4164-a4c8-b534f7b63ae2/")

RETRIEVED_FILE_TYPES = os.getenv('RETRIEVED_FILE_TYPES', '.xlsx')
