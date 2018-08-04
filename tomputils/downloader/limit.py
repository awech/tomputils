"""Rate limiters with shared token bucket.
source:
    https://stackoverflow.com/questions/456649/throttling-with-urllib2#456668
"""

import os
import sys
import threading
import time
import urllib
import urlparse


class TokenBucket(object):
    """An implementation of the token bucket algorithm.
    source: http://code.activestate.com/recipes/511490/

    >>> bucket = TokenBucket(80, 0.5)
    >>> print bucket.consume(10)
    True
    >>> print bucket.consume(90)
    False
    """
    def __init__(self, tokens, fill_rate):
        """tokens is the total tokens in the bucket. fill_rate is the
        rate in tokens/second that the bucket will be refilled."""
        self.capacity = float(tokens)
        self._tokens = float(tokens)
        self.fill_rate = float(fill_rate)
        self.timestamp = time.time()
        self.lock = threading.RLock()

    def consume(self, tokens):
        """Consume tokens from the bucket. Returns 0 if there were
        sufficient tokens, otherwise the expected time until enough
        tokens become available."""
        self.lock.acquire()
        tokens = max(tokens, self.tokens)
        expected_time = (tokens - self.tokens) / self.fill_rate
        if expected_time <= 0:
            self._tokens -= tokens
        self.lock.release()
        return max(0, expected_time)

    @property
    def tokens(self):
        self.lock.acquire()
        if self._tokens < self.capacity:
            now = time.time()
            delta = self.fill_rate * (now - self.timestamp)
            self._tokens = min(self.capacity, self._tokens + delta)
            self.timestamp = now
        value = self._tokens
        self.lock.release()
        return value


class RateLimit(object):
    """Rate limit a url fetch.
    source:
        http://mail.python.org/pipermail/python-list/2008-January/472859.html
    (but mostly rewritten)
    """
    def __init__(self, bucket, filename):
        self.bucket = bucket
        self.last_update = 0
        self.last_downloaded_kb = 0

        self.filename = filename
        self.avg_rate = None

    def __call__(self, block_count, block_size, total_size):
        total_kb = total_size / 1024.

        downloaded_kb = (block_count * block_size) / 1024.
        just_downloaded = downloaded_kb - self.last_downloaded_kb
        self.last_downloaded_kb = downloaded_kb

        predicted_size = block_size/1024.

        wait_time = self.bucket.consume(predicted_size)
        while wait_time > 0:
            time.sleep(wait_time)
            wait_time = self.bucket.consume(predicted_size)

        now = time.time()
        delta = now - self.last_update
        if self.last_update != 0:
            if delta > 0:
                rate = just_downloaded / delta
                if self.avg_rate is not None:
                    rate = 0.9 * self.avg_rate + 0.1 * rate
                self.avg_rate = rate
            else:
                rate = self.avg_rate or 0.
            print("%20s: %4.1f%%, %5.1f KiB/s, %.1f/%.1f KiB" % (
                    self.filename, 100. * downloaded_kb / total_kb,
                    rate, downloaded_kb, total_kb,
                ))
        self.last_update = now


def main():
    """Fetch the contents of urls"""
    if len(sys.argv) < 4:
        print('Syntax: %s rate url1 url2 ...' % sys.argv[0])
        raise SystemExit(1)
    rate_limit = float(sys.argv[1])
    urls = sys.argv[2:]
    bucket = TokenBucket(10*rate_limit, rate_limit)

    print("rate limit = %.1f" % (rate_limit,))

    threads = []
    for url in urls:
        path = urlparse.urlparse(url, 'http')[2]
        filename = os.path.basename(path)
        print('Downloading "%s" to "%s"...' % (url, filename))
        rate_limiter = RateLimit(bucket, filename)
        t = threading.Thread(
            target=urllib.urlretrieve,
            args=(url, filename, rate_limiter))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print('All downloads finished')


if __name__ == "__main__":
    main()
