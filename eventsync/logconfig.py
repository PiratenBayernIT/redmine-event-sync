# -*- coding: utf-8 -*-

import logging
import logging.handlers

def configure_logging(log_filename=None, smtp_settings=None):
    logg = logging.getLogger()
    logg.setLevel(logging.DEBUG)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARN)
    log_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    stream_log = logging.StreamHandler()
    stream_log.setFormatter(log_format)
    logg.addHandler(stream_log)
    if log_filename:
        file_log = logging.handlers.RotatingFileHandler(log_filename)
        file_log.doRollover()
        file_log.setFormatter(log_format)
        logg.addHandler(file_log)
    if smtp_settings:
        smtp_log = logging.handlers.SMTPHandler(**smtp_settings)
        smtp_log.setLevel(logging.WARN)
        smtp_log.setFormatter(log_format)
        logg.addHandler(smtp_log)
    return logg

