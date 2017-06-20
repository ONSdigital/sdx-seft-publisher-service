import logging
import os

LOGGING_FORMAT = ("{level: %(levelname)s, "
                  "service: sdx-seft-spike, "
                  "%(message)s}")
LOGGING_LEVEL = logging.getLevelName(os.getenv('LOGGING_LEVEL', 'WARNING'))
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

RAS_URL = "http://localhost:8080/upload/bres/1/"
