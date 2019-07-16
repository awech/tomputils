# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
#  Purpose: Publish images to volcview
#   Author: Tom Parker
#
# -----------------------------------------------------------------------------
"""
tomputils.volcviewpublisher
====================

Publish images to volcview

:license:
    CC0 1.0 Universal
    http://creativecommons.org/publicdomain/zero/1.0/
"""

import calendar

import requests
from requests.auth import HTTPBasicAuth

PROD_ENDPOINT = "http://volcview.wr.usgs.gov/vv-api"
DEV_ENDPOINT = "http://dev-volcview.wr.usgs.gov/vv-api"


def _get_url_base(dev=False):
    if dev:
        url = DEV_ENDPOINT
    else:
        url = PROD_ENDPOINT

    return url


def publish(user, passwd, sector, band, dataType, time, file, dev=False):
    auth = HTTPBasicAuth(user, passwd)
    data = {
        "sector": sector,
        "band": band,
        "dataType": dataType,
        "imageUnixtime": calendar.timegm(time.timetuple()),
        "file": file,
    }

    url = _get_url_base(dev) + "imageApi/uploadImage"
    return requests.post(url, auth=auth, data=data)


def get_sectors(dev=False):
    return requests.get(_get_url_base(dev) + "/sectorApi/all")


def get_bands(dev=False):
    return requests.get(_get_url_base(dev) + "/bandApi/all")


def get_dataTypes(dev=False):
    return requests.get(_get_url_base(dev) + "/dataTypeApi/all")
