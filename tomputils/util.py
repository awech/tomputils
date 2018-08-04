# -*- coding: utf-8 -*-
"""
utility functions.

"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import os
from buffering_smtp_handler import BufferingSMTPHandler
import sys


def exit_with_error(error):
    logger.error(error)
    logging.shutdown()
    sys.exit(1)


def get_env_var(var, default=None):
    if var in os.environ:
        logger.debug("%s: %s", var, os.environ[var])
        return os.environ[var]

    else:
        if default is None:
            msg = "Envionment variable {} not set, exiting.".format(var)
            exit_with_error(EnvironmentError(msg))
        else:
            logger.debug("%s: %s (default)", var, default)
            return default


def setup_logging():
    global logger
    logger = logging.getLogger("")
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    logger.addHandler(ch)

    try:
        subject = "camfetcher logs"
        handler = BufferingSMTPHandler(os.environ['MAILHOST'],
                                       os.environ['FF_SENDER'],
                                       os.environ['FF_RECIPIENT'], subject,
                                       1000, "%(levelname)s - %(message)s")
        handler.setLevel(logging.ERROR)
        logger.addHandler(handler)
    except KeyError:
        logger.info("SMTP util not configured.")


