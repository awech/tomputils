# -*- coding: utf-8 -*-
"""
Provides a console interface for downloading a file, possibly in segments.

"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import argparse
import logging

from future.builtins import *  # NOQA

from .downloader import DEFAULT_MIN_SEG_SIZE, DEFAULT_MAX_CON
from .downloader import Downloader, DEFAULT_MAX_RETRY

LOG = logging.getLogger(__name__)


def _arg_parse():
    description = "Provides a console interface for downloading a file, " \
                  "possibly in segments."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("url", help="URL of file to download.")
    parser.add_argument("-r", "--retries",
                        help="Maximum number of attemps to fulfill request",
                        type=int, default=DEFAULT_MAX_RETRY)
    parser.add_argument("-n", "--num-con",
                        help="Maximum number of concurrent requests to the "
                             "remote server",
                        type=int, default=DEFAULT_MAX_CON)
    parser.add_argument("-s", "--seg-size",
                        help="Largest file size, in bytes, that will not "
                             "trigger segmenting.",
                        type=int, default=DEFAULT_MIN_SEG_SIZE)
    parser.add_argument("-v", "--verbose", help="Verbose util",
                        action='store_true')

    return parser.parse_args()


def download():
    """
    Download a single file. Entrypoint for downloader console script.

    """
    logging.basicConfig()
    args = _arg_parse()
    if args.verbose is True:
        logging.getLogger().setLevel(logging.DEBUG)

    downloader = Downloader(max_retry=args.retries,
                            min_seg_size=args.seg_size, max_con=args.num_con)

    LOG.debug("Downloading %s", args.url)
    downloader.fetch(args.url)


if __name__ == '__main__':
    download()
