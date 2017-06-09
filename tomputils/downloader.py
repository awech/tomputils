# -*- coding: utf8 -*-
"""
Download a single file. Download file segments concurrently if supported by
the remote server.

Inspired by:
https://github.com/dragondjf/QMusic/blob/master/test/pycurldownload.py

"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from future.builtins import *  # NOQA

import sys
import os
import time
import traceback

import pycurl
from six import StringIO

if os.name == 'posix':
    import signal

    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    del signal

STATUS_OK = (200, 203, 206)
STATUS_ERROR = range(400, 600)
MIN_SEG_SIZE = 16 * 1024
MAX_CON = 4
MAX_RETRY = 5


class Connection(object):
    def __init__(self, req_url):
        self.curl = pycurl.Curl()
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl.setopt(pycurl.MAXREDIRS, 5)
        self.curl.setopt(pycurl.CONNECTTIMEOUT, 30)
        self.curl.setopt(pycurl.TIMEOUT, 300)
        self.curl.setopt(pycurl.NOSIGNAL, 1)
        self.curl.setopt(pycurl.WRITEFUNCTION, self.write_cb)
        self.curl.setopt(pycurl.URL, req_url)
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
            self.name = 'Segment % 02d' % segment[0]
            self.curl.setopt(pycurl.RANGE, '%d-%d' % (segment[1], segment[2]))
            self.segment_size = segment[2] - segment[1] + 1
            self.segment = segment
        else:
            self.id = 0
            self.name = 'TASK'
            self.segment_size = segment
            self.segment = None

        self.link_downloaded = 0
        self.segment_downloaded = 0
        self.retried = 0
        self.out_file = out_file
        self.segment = segment

    def prepare_retry(self):
        self.curl.setopt(pycurl.RANGE, '%d-%d' % (self.segment[1] +
                                                  self.segment_downloaded,
                                                  self.segment[2]))
        if self.link_downloaded:
            self.link_downloaded = 0
        else:
            self.retried += 1

    def close(self):
        self.curl.close()

    def write_cb(self, buf):
        if self.segment:
            self.out_file.seek(self.segment[1] + self.segment_downloaded, 0)
            self.out_file.write(buf)
            self.out_file.flush()
            size = len(buf)
            self.link_downloaded += size
            self.segment_downloaded += size
            self.total_downloaded += size


class Downloader(object):
    def __init__(self, max_retry=MAX_RETRY, min_seg_size=MIN_SEG_SIZE,
                 max_con=MAX_CON):
        self.min_seg_size = min_seg_size
        self.max_retry = max_retry
        self.max_con = max_con

    def fetch(self, req_url, output=None):
        """
        TODO: test can_segment == false
        :param req_url: Requested URL
        :param output: Path for downloaded file
        :return: getinfo reference
        """

        headers = StringIO()
        response = req_headers(req_url, headers)
        if response(pycurl.RESPONSE_CODE) not in STATUS_OK:
            print("Cannot retrieve headers for %s. Aborting." % req_url)
            return

        eurl = response(pycurl.EFFECTIVE_URL)
        size = int(response(pycurl.CONTENT_LENGTH_DOWNLOAD))
        can_segment = headers.getvalue().find('Accept-Ranges') != -1

        if output is None:
            output = os.path.split(eurl)[1]

        print('Downloading %s, (%d bytes)' % (output, size))
        segments = self.get_segments(size, can_segment)

        # allocate file space
        afile = open(output, str('wb'))
        afile.truncate(size)
        afile.close()

        out_file = open(output, str('r+b'))
        connections = []
        for i in range(len(segments)):
            c = Connection(eurl)
            connections.append(c)

        con = {
            'connections': connections,
            'free': connections[:],
            'working': []
        }

        ok = True
        start_time = time.time()
        elapsed = None
        mcurl = pycurl.CurlMulti()

        try:
            while 1:
                while segments and con['free']:
                    p = segments.pop(0)
                    c = con['free'].pop(0)
                    c.prepare(out_file, p)
                    con['working'].append(c)
                    mcurl.add_handle(c.curl)
                    print('%s:Start downloading' % c.name)

                while 1:
                    ret, handles_num = mcurl.perform()
                    if ret != pycurl.E_CALL_MULTI_PERFORM:
                        break

                while 1:
                    num_q, ok_list, err_list = mcurl.info_read()
                    for curl in ok_list:
                        curl.errno = pycurl.E_OK
                        curl.errmsg = None
                        self.process_result(mcurl, curl, con, segments)
                    for curl, errno, errmsg in err_list:
                        curl.errno = errno
                        curl.errmsg = errmsg
                        self.process_result(mcurl, curl, con, segments)
                    if num_q == 0:
                        break

                elapsed = time.time() - start_time
                downloaded = sum([connection.total_downloaded for connection in
                                  connections])
                show_progress(size, downloaded, elapsed)

                if not con['working']:
                    break

                mcurl.select(1.0)
        except:
            # logging.error('Error: ' + Traceback())
            ok = False
        finally:
            for c in connections:
                c.close()
                mcurl.close()

        if ok:
            msg = 'Download Succeeded! Total Elapsed %ds' % elapsed
        else:
            print(traceback.format_exc())
            msg = 'Download Failed!'
        print(msg)
        # logging.info(msg)

    def process_result(self, mcurl, curl, con, segments):
        mcurl.remove_handle(curl)
        c = curl.connection
        c.errno = curl.errno
        c.errmsg = curl.errmsg
        con['working'].remove(c)
        if c.errno == pycurl.E_OK:
            c.code = curl.getinfo(pycurl.RESPONSE_CODE)
            if c.code in STATUS_OK:
                assert c.segment_downloaded == c.segment_size
                print('%s: Download successed' % c.name)
                print('%s:Download %s out of %d' % (c.name,
                                                    c.segment_downloaded,
                                                    c.segment_size))
                con['free'].append(c)
            elif c.code in STATUS_ERROR:
                print('%s:Error < %d >! Connection will be closed' % (c.name,
                                                                      c.code))
                segments.append(c.segment)
                new_c = Connection(c.getopt(pycurl.URL))
                con['connections'].append(new_c)
                con['free'].append(new_c)

                c.close()
                con['connections'].remove(c)
            else:
                raise Exception(
                    '%s: Unhandled http status code %d' % (c.name, c.code))
        else:
            print('%s:Download failed < %s >' % (c.name, c.errmsg))
            if c.can_segment and c.retried < self.max_retry:
                c.prepare_retry()
                con['working'].append(c)
                mcurl.add_handle(c.curl)
                print('%s:Try again' % c.name)
            else:
                raise Exception("%s" % c.errmsg)

    def get_segments(self, size, can_segment):
        file_size = size
        # segments = None
        if can_segment:
            num = self.max_con
            while num * self.min_seg_size > file_size and num > 1:
                num -= 1
            segment_size = int(file_size / num + 0.5)
            segments = [[i, i * segment_size, (i + 1) * segment_size - 1]
                        for i in range(num)]
            segments[-1][2] = file_size - 1
        else:
            segments = [file_size]
        return segments


def req_headers(req_url, headers):
    curl = pycurl.Curl()
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.MAXREDIRS, 5)
    curl.setopt(pycurl.CONNECTTIMEOUT, 30)
    curl.setopt(pycurl.TIMEOUT, 300)
    curl.setopt(pycurl.NOSIGNAL, 1)
    curl.setopt(pycurl.NOPROGRESS, 1)
    curl.setopt(pycurl.NOBODY, 1)
    curl.setopt(pycurl.HEADERFUNCTION, headers.write)
    curl.setopt(pycurl.URL, req_url)

    curl.perform()
    if curl.errstr():
        return None
    else:
        return curl.getinfo


def show_progress(size, downloaded, elapsed):
    percent = min(100, downloaded * 100 / size)
    if elapsed == 0:
        rate = 0
    else:
        rate = downloaded * 1.0 / 1024.0 / elapsed
    info = ' D / L:%d / %d ( % 6.2f%%) - Avg:%4.1fkB / s' % (downloaded,
                                                             size,
                                                             percent, rate)
    space = ' ' * (60 - len(info))

    prog_len = int(percent * 20 / 100)
    prog = '|' + 'o' * prog_len + '.' * (20 - prog_len) + '|'

    sys.stdout.write(info + space + prog)
    sys.stdout.flush()
    sys.stdout.write('\b' * 82)


def fetch(req_url):
    dl = Downloader()
    dl.fetch(req_url)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        for url in sys.argv[1:]:
            fetch(url)
    else:
        print("I need a URL")
