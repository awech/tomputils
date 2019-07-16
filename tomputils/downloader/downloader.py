# -*- coding: utf8 -*-
"""
Download a single file. Download file segments concurrently if supported by
the remote server.

Inspired by:
https://github.com/dragondjf/QMusic/blob/master/test/pycurldownload.py

"""
from __future__ import absolute_import, division, print_function, unicode_literals
from future.builtins import *  # NOQA
import logging
import sys
import os
import time

import pycurl
from six import BytesIO

if os.name == "posix":
    import signal

    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    del signal

STATUS_OK = (200, 203, 206)
STATUS_ERROR = range(400, 600)
DEFAULT_MIN_SEG_SIZE = 16 * 1024
DEFAULT_MAX_CON = 4
DEFAULT_MAX_RETRY = 5

LOG = logging.getLogger(__name__)


class Connection(object):
    def __init__(self, req_url, can_segment):
        self.curl = pycurl.Curl()
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl.setopt(pycurl.MAXREDIRS, 5)
        self.curl.setopt(pycurl.CONNECTTIMEOUT, 30)
        self.curl.setopt(pycurl.TIMEOUT, 300)
        self.curl.setopt(pycurl.NOSIGNAL, 1)
        self.curl.setopt(pycurl.WRITEFUNCTION, self.write_cb)
        self.curl.setopt(pycurl.URL, req_url)
        self.can_segment = can_segment
        self.curl.connection = self
        self.total_downloaded = 0
        self.id = None
        self.name = None
        self.segment_size = None
        self.segment = None
        self.link_downloaded = None
        self.segment_downloaded = None
        self.retried = None
        self.out_file = None

    def prepare(self, out_file, segment):
        if isinstance(segment, list):
            self.id = segment[0]
            self.name = "Segment % 02d" % segment[0]
            self.curl.setopt(pycurl.RANGE, "%d-%d" % (segment[1], segment[2]))
            self.segment_size = segment[2] - segment[1] + 1
            self.segment = segment
        else:
            self.id = 0
            self.name = "TASK"
            self.segment_size = segment
            self.segment = None

        self.link_downloaded = 0
        self.segment_downloaded = 0
        self.retried = 0
        self.out_file = out_file
        self.segment = segment

    def prepare_retry(self):
        if self.can_segment:
            self.curl.setopt(
                pycurl.RANGE,
                "%d-%d" % (self.segment[1] + self.segment_downloaded, self.segment[2]),
            )
        if self.link_downloaded:
            self.link_downloaded = 0
        else:
            self.retried += 1

    def close(self):
        self.curl.close()

    def write_cb(self, buf):
        if self.can_segment:
            self.out_file.seek(self.segment[1] + self.segment_downloaded, 0)
            self.out_file.write(buf)
            self.out_file.flush()
            size = len(buf)
            self.link_downloaded += size
            self.segment_downloaded += size
            self.total_downloaded += size
        else:
            self.out_file.write(buf)
            self.out_file.flush()
            size = len(buf)
            self.link_downloaded += size
            self.segment_downloaded += size
            self.total_downloaded += size


class Downloader(object):
    """
    Download a file, possibly in segments.

    Parameters
    ----------
    max_retry : int, optional
        Maximum attempts that will be made to retrieve a segment.
    min_seg_size : int, optional
        Largest file size, in bytes, that will not trigger segmenting.
    max_con : int, optional
        Maximum number of concurrent connections to the remote server.

    """

    def __init__(
        self,
        max_retry=DEFAULT_MAX_RETRY,
        min_seg_size=DEFAULT_MIN_SEG_SIZE,
        max_con=DEFAULT_MAX_CON,
    ):
        self.min_seg_size = min_seg_size
        self.max_retry = max_retry
        self.max_con = max_con

    def fetch(self, req_url, output=None):
        """
        Fetch a file.

        Parameters
        ----------
        req_url : str
            URL of the file to retrieve
        output : str, optional
            filename, possibly with path, of the downloaded file.

        TODO: test can_segment == false
        """

        (eurl, size, can_segment) = _check_headers(req_url)
        if output is None:
            output = os.path.split(eurl)[1]

        if len(output) < 1:
            raise RuntimeError(
                "Output file must be provided if URL points " "to a directory."
            )
        LOG.info("Downloading %s, (%d bytes)" % (output, size))
        segments = self._get_segments(size, can_segment)

        # allocate file space
        afile = open(output, str("wb"))
        if size > 0:
            afile.truncate(size)
        afile.close()

        out_file = open(output, str("r+b"))
        connections = []
        for i in range(len(segments)):
            c = Connection(eurl, can_segment)
            connections.append(c)

        con = {"connections": connections, "free": connections[:], "working": []}

        start_time = time.time()
        elapsed = None
        mcurl = pycurl.CurlMulti()

        while True:
            while segments and con["free"]:
                p = segments.pop(0)
                c = con["free"].pop(0)
                c.prepare(out_file, p)
                con["working"].append(c)
                mcurl.add_handle(c.curl)
                LOG.debug("%s:Start downloading", c.name)

            while True:
                ret, handles_num = mcurl.perform()
                if ret != pycurl.E_CALL_MULTI_PERFORM:
                    break

            while True:
                num_q, ok_list, err_list = mcurl.info_read()
                for curl in ok_list:
                    curl.errno = pycurl.E_OK
                    mcurl.remove_handle(curl)

                    c = curl.connection
                    con["working"].remove(c)
                    c.errno = curl.errno
                    c.errmsg = None
                    c.code = curl.getinfo(pycurl.RESPONSE_CODE)

                    if c.code in STATUS_OK:
                        LOG.info(
                            "%s: Download successful. (%d/%d)",
                            c.name,
                            c.segment_downloaded,
                            c.segment_size,
                        )
                        con["free"].append(c)

                    elif c.code in STATUS_ERROR:
                        msg = "%s:Error < %d >! Connection will be closed"
                        LOG.error(msg.format(c.name, c.code))
                        con["connections"].remove(c)
                        c.close()
                        segments.append(c.segment)
                        new_c = Connection(c.getopt(pycurl.URL))
                        con["connections"].append(new_c)
                        con["free"].append(new_c)

                    else:
                        msg = "%s: Unhandled http status code %d"
                        raise Exception(msg.format(c.name, c.code))

                for curl, errno, errmsg in err_list:
                    curl.errno = errno
                    curl.errmsg = errmsg
                    mcurl.remove_handle(curl)

                    c = curl.connection
                    c.errno = curl.errno
                    c.errmsg = curl.errmsg
                    con["working"].remove(c)
                    msg = "%s:Download failed < %s >"
                    LOG.error(msg, c.name, c.errmsg)
                    if c.can_segment and c.retried < self.max_retry:
                        c.prepare_retry()
                        con["working"].append(c)
                        mcurl.add_handle(c.curl)
                        LOG.error("%s:Try again", c.name)
                    else:
                        raise RuntimeError(c.errmsg)

                if num_q == 0:
                    break

            elapsed = time.time() - start_time
            downloaded = sum(
                [connection.total_downloaded for connection in connections]
            )
            _show_progress(size, downloaded, elapsed)

            if not con["working"]:
                break

            mcurl.select(1.0)

        msg = "Download Succeeded! Total Elapsed {}s".format(elapsed)
        LOG.info(msg)

    def _get_segments(self, file_size, can_segment):
        """
        Calculate segements to request.

        Parameters
        ----------
        file_size : int
            Lenght of file in bytes.
        can_segment: : bool
            If true, remote server supports segmented downloads.

        Returns
        -------
        bytearray
            A two-dimensional array of segments to download.

        """
        if can_segment:
            num = self.max_con
            while num * self.min_seg_size > file_size and num > 1:
                num -= 1
            segment_size = int(file_size / num + 0.5)
            segments = [
                [i, i * segment_size, (i + 1) * segment_size - 1] for i in range(num)
            ]
            segments[-1][2] = file_size - 1
        else:
            segments = [file_size]

        LOG.debug("Using %d segments.", len(segments))
        return segments


def _check_headers(url):
    """
    Request and parse file headers in preparation of file retireval.

    Parameters
    ----------
    url : str
        URL of the file to be retrieved.

    Returns
    -------
    (str, str, str)
        Three-tuple of effective URL, size of the file in bytes, and true if
        the remote server supports segmented downloads.
    """
    headers = BytesIO()
    curl = pycurl.Curl()
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.MAXREDIRS, 5)
    curl.setopt(pycurl.CONNECTTIMEOUT, 30)
    curl.setopt(pycurl.TIMEOUT, 300)
    curl.setopt(pycurl.NOSIGNAL, 1)
    curl.setopt(pycurl.NOPROGRESS, 1)
    curl.setopt(pycurl.NOBODY, 1)
    curl.setopt(pycurl.HEADERFUNCTION, headers.write)
    curl.setopt(pycurl.URL, url)

    curl.perform()
    response_code = curl.getinfo(pycurl.RESPONSE_CODE)
    if curl.errstr() or response_code not in STATUS_OK:
        msg = "Cannot retrieve %s. (%s)".format(url, pycurl.RESPONSE_CODE)
        raise RuntimeError(msg)

    eurl = curl.getinfo(pycurl.EFFECTIVE_URL)
    size = int(curl.getinfo(pycurl.CONTENT_LENGTH_DOWNLOAD))
    headers = headers.getvalue().decode("UTF-8")
    can_segment = headers.find("Accept-Ranges") != -1
    if size < 1:
        can_segment = False

    return (eurl, size, can_segment)


def _show_progress(size, downloaded, elapsed):
    if not sys.stdout.isatty():
        return

    percent = min(100, downloaded * 100 / size)
    if elapsed != 0:
        rate = downloaded * 1.0 / 1024.0 / elapsed
        info = " D / L:%d / %d ( % 6.2f%%) - Avg:%4.1fkB / s" % (
            downloaded,
            size,
            percent,
            rate,
        )
        space = " " * (60 - len(info))

        prog_len = int(percent * 20 / 100)
        prog = "|" + "o" * prog_len + "." * (20 - prog_len) + "|"

        sys.stdout.write(info + space + prog)
        sys.stdout.flush()
        sys.stdout.write("\b" * 82)


def fetch(req_url, output=None):
    """
    Fetch a single URL using default settings.

    Parameters
    ----------
    req_url : unicode or str
        URL to request. File will be written to teh current working directory.
    """
    dl = Downloader()
    dl.fetch(req_url, output)
