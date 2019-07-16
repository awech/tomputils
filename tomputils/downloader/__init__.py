# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
#  Purpose: Segmenting downloader.
#   Author: Tom Parker
#
# -----------------------------------------------------------------------------
"""
tomputils.downloader
====================

A simple segmenting downloader.

:license:
    CC0 1.0 Universal
    http://creativecommons.org/publicdomain/zero/1.0/
"""

from tomputils.downloader.downloader import Downloader, fetch

DEFAULT_MIN_SEG_SIZE = 16 * 1024
DEFAULT_MAX_CON = 4
DEFAULT_MAX_RETRY = 5

__all__ = [
    "fetch",
    "Downloader",
    "DEFAULT_MIN_SEG_SIZE",
    "DEFAULT_MAX_CON",
    "DEFAULT_MAX_RETRY",
]
