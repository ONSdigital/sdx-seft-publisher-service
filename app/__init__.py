import datetime
import logging
import os

from sdx.common.logger_config import logger_initial_config
from structlog import wrap_logger
from structlog.processors import JSONRenderer
from structlog.stdlib import filter_by_level, add_log_level


__version__ = "0.1.1"
__service__ = "sdx-seft-publisher-service"


logger_initial_config(service_name=__service__, log_level=os.getenv("LOGGING_LEVEL", "DEBUG"))


def add_timestamp(_, __, event_dict):
    event_dict['created'] = datetime.datetime.utcnow().isoformat()
    return event_dict


def add_service_and_version(_, __, event_dict):
    event_dict['service'] = __service__
    event_dict['version'] = __version__
    return event_dict


def create_and_wrap_logger(logger_name):
    logger = wrap_logger(logging.getLogger(logger_name),
                         processors=[add_log_level,
                         filter_by_level,
                         add_timestamp,
                         add_service_and_version,
                         JSONRenderer(indent=1, sort_keys=True)])
    return logger
