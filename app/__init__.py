import logging
import os

from structlog import wrap_logger


__version__ = "1.4.1"
__service__ = "sdx-seft-publisher-service"

LOGGING_FORMAT = "%(asctime)s.%(msecs)06dZ|%(levelname)s: sdx-seft-publisher-service: %(message)s"

logging.basicConfig(format=LOGGING_FORMAT,
                    datefmt="%Y-%m-%dT%H:%M:%S",
                    level=os.getenv("LOGGING_LEVEL", "DEBUG"))


def create_and_wrap_logger(logger_name):
    logger = wrap_logger(logging.getLogger(logger_name))
    logger.info("START", version=__version__)
    return logger
