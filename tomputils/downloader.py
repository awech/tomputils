# -*- coding: utf8 -*-
"""
Download a single file, using concurrent segments if supported by the remote
server.

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
from cStringIO import StringIO

if os.name == 'posix':
    import signal

    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    del signal

VALIDPROTOCOL = ('http', 'ftp')
STATUS_OK = (200, 203, 206)
STATUS_ERROR = range(400, 600)
MIN_SEG_SIZE = 16 * 1024
MAX_CON_COUNT = 4
MAXRETRYCOUNT = 5


class Connection:
    def __init__(self, url):
        self.curl = pycurl.Curl()
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl.setopt(pycurl.MAXREDIRS, 5)
        self.curl.setopt(pycurl.CONNECTTIMEOUT, 30)
        self.curl.setopt(pycurl.TIMEOUT, 300)
        self.curl.setopt(pycurl.NOSIGNAL, 1)
        self.curl.setopt(pycurl.WRITEFUNCTION, self.write_cb)
        self.curl.setopt(pycurl.URL, url)
        self.curl.connection = self
        self.total_downloaded = 0
        self.id = None
        self.name = None
        self.segment_size = None
        self.segment = None
        self.link_downloaded = None
        self.segment_downloaded = None
        self.is_stop = None
        self.retried = None
        self.result = None

    def start(self, result, segment):
        if isinstance(segment, list):
            self.id = segment[0]
            self.name = 'Segment % 02d' % segment[0]
            self.curl.setopt(pycurl.RANGE, '% d - %d' % (segment[1], segment[2]))
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
        self.is_stop = False
        self.result = result
        self.segment = segment

    def retry(self):
        self.curl.setopt(pycurl.RANGE, '% d - %d' % (self.segment[1] +
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
            self.result.seek(self.segment[1] + self.segment_downloaded, 0)
            self.result.write(buf)
            self.result.flush()
            size = len(buf)
            self.link_downloaded += size
            self.segment_downloaded += size
            self.total_downloaded += size
        if self.is_stop:
            return -1


def get_headers(url, headers):
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

    try:
        curl.perform()
        if not curl.errstr():
            return curl.getinfo
        else:
            return None
    except:
        return None


def get_segments(url_info):
    file_size = url_info['size']
    # segments = None
    if url_info['can_segment']:
        num = MAX_CON_COUNT
        while num * MIN_SEG_SIZE > file_size and num > 1:
            num -= 1
        segment_size = int(file_size / num + 0.5)
        segments = [[i, i * segment_size, (i + 1) * segment_size - 1]
                    for i in range(num)]
        segments[-1][2] = file_size - 1
    else:
        segments = [file_size]
    return segments


def show_progress(url_info, downloaded, elapsed):
    percent = min(100, downloaded * 100 / url_info['size'])
    if elapsed == 0:
        rate = 0
    else:
        rate = downloaded * 1.0 / 1024.0 / elapsed
    info = ' D / L:%d / %d ( % 6.2f%%) - Avg:%4.1fkB / s' % (downloaded,
                                                             url_info['size'],
                                                             percent, rate)
    space = ' ' * (60 - len(info))

    prog_len = int(percent * 20 / 100)
    prog = '|' + 'o' * prog_len + '.' * (20 - prog_len) + '|'

    sys.stdout.write(info + space + prog)
    sys.stdout.flush()
    sys.stdout.write('\b' * 82)


class Downloader:
    def __init__(self):
        self.mcurl = pycurl.CurlMulti()
        self.segments = None
        self.url_info = None
        self.result = None
        self.connections = None
        self.free_connections = None
        self.working_connections = None

    def fetch(self, url):
        """
        TODO: test can_segment == false
        :param url:
        :return:
        """
        headers = StringIO()
        response = get_headers(url, headers)
        if response(pycurl.RESPONSE_CODE) not in STATUS_OK:
            print("Cannot retrieve headers")
            return

        url = response(pycurl.EFFECTIVE_URL)
        filename = os.path.split(url)[1]
        size = int(response(pycurl.CONTENT_LENGTH_DOWNLOAD))
        can_segment = headers.getvalue().find('Accept-Ranges') != -1

        url_info = {
            'url': url,
            'file': filename,
            'size': size,
            'can_segment': can_segment
        }
        print('Download %s, (%d bytes)' % (url_info['file'],
                                           url_info['size']))
        self.segments = get_segments(url_info)

        # allocate file space
        afile = file(url_info['file'], 'wb')
        afile.truncate(url_info['size'])
        afile.close()

        self.url_info = url_info

        self.result = file(str(url_info['file']), str('r+b'))
        self.connections = []
        for i in range(len(self.segments)):
            c = Connection(url_info['url'])
            self.connections.append(c)
            self.free_connections = self.connections[:]
            self.working_connections = []

        ok = True
        start_time = time.time()
        elapsed = None
        try:
            while 1:
                while self.segments and self.free_connections:
                    p = self.segments.pop(0)
                    c = self.free_connections.pop(0)
                    c.start(self.result, p)
                    self.working_connections.append(c)
                    self.mcurl.add_handle(c.curl)
                    print('%s:Start downloading' % c.name)

                while 1:
                    ret, handles_num = self.mcurl.perform()
                    if ret != pycurl.E_CALL_MULTI_PERFORM:
                        break

                while 1:
                    queue_num, ok_list, err_list = self.mcurl.info_read()
                    for curl in ok_list:
                        curl.errno = pycurl.E_OK
                        curl.errmsg = ''
                        self.process_curl(curl)
                    for curl, errno, errmsg in err_list:
                        curl.errno = errno
                        curl.errmsg = errmsg
                        self.process_curl(curl)
                    if queue_num == 0:
                        break

                elapsed = time.time() - start_time
                downloaded = sum([con.total_downloaded for con in
                                  self.connections])
                show_progress(url_info, downloaded, elapsed)

                if not self.working_connections:
                    break

                self.mcurl.select(1.0)
        except:
            # logging.error('Error: ' + Traceback())
            ok = False
        finally:
            for c in self.connections:
                c.close()
                self.mcurl.close()

        if ok:
            msg = 'Download Successed! Total Elapsed % ds' % elapsed
        else:
            print(traceback.format_exc())
            msg = 'Download Failed!'
        print(msg)
        # logging.info(msg)

    def process_curl(self, curl):
        self.mcurl.remove_handle(curl)
        c = curl.connection
        c.errno = curl.errno
        c.errmsg = curl.errmsg
        self.working_connections.remove(c)
        if c.errno == pycurl.E_OK:
            c.code = curl.getinfo(pycurl.RESPONSE_CODE)
            if c.code in STATUS_OK:
                assert c.segment_downloaded == c.segment_size
                print('%s: Download successed' % c.name)
                print('%s:Download % s out of % d' % (c.name,
                                                      c.segment_downloaded,
                                                      c.segment_size))
                self.free_connections.append(c)
            elif c.code in STATUS_ERROR:
                print('%s:Error < %d >! Connection will be closed' % (c.name,
                                                                      c.code))
                self.connections.remove(c)
                c.close()
                self.segments.append(c.segment)
            else:
                raise Exception(
                    '% s: Unhandled http status code % d' % (c.name, c.code))
        else:
            print('%s:Download failed < %s >' % (c.name, c.errmsg))
            if self.url_info['can_segment'] and c.retried < MAXRETRYCOUNT:
                c.retry()
                self.working_connections.append(c)
                self.mcurl.add_handle(c.curl)
                print('%s:Try again' % c.name)
            else:
                raise Exception("%s" % c.errmsg)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        downloader = Downloader()
        downloader.fetch(sys.argv[1])
    else:
        print("I need a URL")
