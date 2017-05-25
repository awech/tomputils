# -*- coding: utf-8 -*-
"""
Interact with a Mattermost server.

This modules ineracts with a `Mattermost <http://mattermost.com/>`_
server using Mattermost API V3. It will look to the environment for
configuration, expecting to see the following environment variables:

    * MATTERMOST_SERVER_URL=https://chat.example.com
    * MATTERMOST_TEAM_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
    * MATTERMOST_USER_PASS=mat_pass
    * MATTERMOST_CHANNEL_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
    * MATTERMOST_USER_ID=mat_user

Example:
::
    >>> import json
    >>> import tomputils.mattermost as mm
    >>> conn = mm.Mattermost()
    >>> print(json.dumps(conn.get_teams(), indent=4))
    {
        "39ou1iab7pnomynpzeme869m4w": {
            "allowed_domains": "",
            "display_name": "AVO",
            "name": "avo",
            "invite_id": "89hj448uktds9px9eei65qg55h",
            "delete_at": 0,
            "update_at": 1488239656296,
            "create_at": 1487379468267,
            "email": "scott.crass@alaska.gov",
            "company_name": "",
            "allow_open_invite": true,
            "type": "O",
            "id": "39ou1iab7pnomynpzeme869m4w",
            "description": ""
        }
    }
    >>>

"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from future.builtins import *  # NOQA

import os
import json
import logging
import requests


class Mattermost(object):
    """
    Interact with a mattermost server.
    """

    def __init__(self, verbose=False):
        self.logger = setup_logging(verbose)

        self.server_url = os.environ['MATTERMOST_SERVER_URL']
        self.logger.debug("Mattermost server URL: " + self.server_url)
        self.team_id = os.environ['MATTERMOST_TEAM_ID']
        self.logger.debug("Mattermost team id: " + self.team_id)
        self.channel_id = os.environ['MATTERMOST_CHANNEL_ID']
        self.logger.debug("Mattermost channelid: " + self.channel_id)
        self.user_id = os.environ['MATTERMOST_USER_ID']
        self.logger.debug("Mattermost user email: " + self.user_id)
        self.user_pass = os.environ['MATTERMOST_USER_PASS']
        self.logger.debug("Mattermost user pass: " + self.user_pass)

        # Login
        self.session = requests.Session()
        self.session.headers.update({"X-Requested-With": "XMLHttpRequest"})

        if 'SSL_CA' in os.environ:
            self.logger.debug("Using SSL key " + os.environ['SSL_CA'])
            self.session.verify = os.environ['SSL_CA']

        url = self.server_url + '/api/v3/users/login'
        login_data = json.dumps({'login_id': self.user_id,
                                 'password': self.user_pass})
        response = self.session.post(url, data=login_data)
        self.logger.debug(response)
        # self.mattermostUserId = l.json()["id"]

    def get_teams(self):
        """
        Get a list of teams on the server.
        :return: Known teams
        """
        response = self.session.get('%s/api/v3/teams/all' % self.server_url)
        return json.loads(response.content)

    def get_channels(self, team_id):
        """
        Get a list of available channels for a team
        :param team_id: Team Id to check
        :return: Avaliable channels
        """
        req = '%s/api/v3/teams/%s/channels/' % (self.server_url, team_id)
        response = self.session.get(req)
        return json.loads(response.content)

    def post(self, message):
        """
        post a message to mattermost. Adapted from
        http://stackoverflow.com/questions/42305599/how-to-send-file-through-mattermost-incoming-webhook
        :param message: message to post
        """
        self.logger.debug("Posting message to mattermost: %s", message)
        post_data = json.dumps({
            'user_id': self.user_id,
            'channel_id': self.channel_id,
            'message': message,
            'create_at': 0,
        })
        url = '%s/api/v3/teams/%s/channels/%s/posts/create' \
              % (self.server_url, self.team_id, self.channel_id)
        response = self.session.post(url, data=post_data)

        if response.status_code == 200:
            self.logger.debug(response.content)
        else:
            self.logger.warn(response.content)


def setup_logging(verbose):
    """
    Configure logging
    :param verbose: If true set logger to debug
    :return: logger
    """
    logger = logging.getLogger('Mattermost')
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Verbose logging")
    else:
        logging.getLogger().setLevel(logging.INFO)

    return logger


def format_timedelta(timedelta):
    """
    Format a timedelta into a human-friendly string
    :param timedelta: timedelta to format
    :return: Pretty string
    """
    seconds = timedelta.total_seconds()

    days, rmainder = divmod(seconds, 60 * 60 * 24)
    hours, rmainder = divmod(rmainder, 60 * 60)
    minutes, rmainder = divmod(rmainder, 60)
    seconds = rmainder

    timestring = ''
    if days > 0:
        timestring += '%dd ' % days

    if hours > 0:
        timestring += '%dh ' % hours

    if minutes > 0:
        timestring += '%dm ' % minutes

    timestring += '%ds' % seconds

    return timestring


def format_span(start, end):
    """
    format a time span into a human-friendly string
    :param start: start datetime
    :param end: end datetime
    :return: Pretty string
    """
    time_string = start.strftime('%m/%d/%Y %H:%M:%S - ')
    time_string += end.strftime('%H:%M:%S')

    return time_string
