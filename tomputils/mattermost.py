# -*- coding: utf-8 -*-
"""
Interact with a Mattermost server.

This modules ineracts with a `Mattermost <http://mattermost.com/>`_ server
using `Mattermost API V3 <https://api.mattermost.com/>`_. It will look to the
environment for configuration, expecting to see the following environment
variables:

    * MATTERMOST_SERVER_URL=https://chat.example.com
    * MATTERMOST_USER_ID=mat_user
    * MATTERMOST_USER_PASS=mat_pass
    * MATTERMOST_TEAM_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
    * MATTERMOST_CHANNEL_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx

"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import os
import json
import logging

from future.builtins import *  # NOQA

import requests


LOG = logging.getLogger(__name__)


class Mattermost(object):
    """
    Interact with a mattermost server.

    .. rubric:: Basic Usage

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

    def __init__(self, server_url=None, team_name=None, channel_name=None):
        self.user_id = os.environ['MATTERMOST_USER_ID']
        LOG.debug("Mattermost user email: %s", self.user_id)
        self.user_pass = os.environ['MATTERMOST_USER_PASS']
        LOG.debug("Mattermost user pass: %s", self.user_pass)

        if server_url is None:
            self.server_url = os.environ['MATTERMOST_SERVER_URL']
        else:
            self.server_url = server_url
        LOG.debug("Mattermost server URL: %s", self.server_url)

        self.session = requests.Session()
        self.session.headers.update({"X-Requested-With": "XMLHttpRequest"})
        if 'SSL_CA' in os.environ:
            LOG.debug("Using SSL key %s", os.environ['SSL_CA'])
            self.session.verify = os.environ['SSL_CA']

        self.login()

        if team_name is None:
            self.team_id = os.environ['MATTERMOST_TEAM_ID']
        else:
            self.team_id = self.get_team_id(team_name)
        LOG.debug("Mattermost team id: %s", self.team_id)

        if channel_name is None:
            self.channel_id = os.environ['MATTERMOST_CHANNEL_ID']
        else:
            self.channel_id = self.get_channel_id(self.team_id, channel_name)
        LOG.debug("Mattermost channelid: %s", self.channel_id)

    def login(self):
        """
        Authenticate with the server.
        """
        url = self.server_url + '/api/v3/users/login'
        login_data = json.dumps({'login_id': self.user_id,
                                 'password': self.user_pass})
        LOG.debug("Sending: %s", login_data)
        response = self.session.post(url, data=login_data)
        LOG.debug("Received: %s", response.json())

    def get_teams(self):
        """
        Get a list of teams on the server.

        :return: Known teams

            .. rubric:: Basic Usage

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
        """
        response = self.session.get('%s/api/v3/teams/all' % self.server_url)
        return json.loads(response.content)

    def get_team_id(self, team_name):
        """
        Get a team id.

        :return: team id

        """

        teams = self.get_teams()
        for tid in teams.keys():
            team = teams[tid]
            if team['name'] == team_name:
                return team['id']

        return None

    def get_channels(self, team_id):
        """
        Get a list of available channels for a team
        :param team_id: Team Id to check
        :return: Avaliable channels

        .. rubric:: Basic Usage

        >>> import json
        >>> import tomputils.mattermost as mm
        >>> conn = mm.Mattermost()
        >>> print(json.dumps(conn.get_channels(), indent=4))
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
        """
        req = '%s/api/v3/teams/%s/channels/' % (self.server_url, team_id)
        response = self.session.get(req)
        return json.loads(response.content)

    def get_channel_id(self, team_id, channel_name):
        """
        Locate channel by name.

        :param team_id:
        :param channel_name:
        :return: channel id
        """
        channels = self.get_channels(team_id)
        for channel in channels:
            if channel['name'] == channel_name:
                return channel['id']

        return None

    def upload(self, file_path):
        """
        upload a file
        :param file_path:
        :return:
        """
        LOG.debug(("Uploading file to mattermost: %s", file_path))
        filename = os.path.basename(file_path)
        post_data = {'channel_id': self.channel_id,
                     'client_ids': filename}
        file_data = {'files': (filename, open(file_path, 'rb'))}
        url = '%s/api/v3/teams/%s/files/upload' % (self.server_url,
                                                   self.team_id)
        response = self.session.post(url, data=post_data, files=file_data)
        # f = open("out.txt", "wb")
        # f.write(response.request.body)
        # f.close()
        LOG.debug("Received: %s - %s", response.status_code, response.text)

        if response.status_code != 200:
            if response.status_code == 400:
                msg = "Type of the uploaded file doesn't match its file " \
                      " extension or uploaded file is an image that " \
                      "exceeds the maximum dimensions"
            elif response.status_code == 401:
                msg = "User is not logged in"
            elif response.status_code == 403:
                msg = "User does not have permission to upload file to " \
                      "the provided team/channel"
            elif response.status_code == 413:
                msg = "Uploaded file is too large"
            elif response.status_code == 500:
                msg = "File storage is disabled"
            else:
                msg = response
            raise RuntimeError("Server unhappy with request, reports: %s"
                               % msg)

        file_id = response.json()["file_infos"][0]["id"]
        return file_id

    def post(self, message, file_path=None):
        """
        post a message to mattermost. Adapted from
        http://stackoverflow.com/questions/42305599/how-to-send-file-through-mattermost-incoming-webhook
        :param message: message to post
        :param file_path: Path of to attach
        :return: post id
        :
        """
        LOG.debug("Posting message to mattermost: %s", message)
        post_data = {
            'user_id': self.user_id,
            'channel_id': self.channel_id,
            'message': message,
            'create_at': 0,
        }

        if file_path is not None:
            LOG.debug("attaching file: %s", file)
            file_id = self.upload(file_path)
            post_data['file_ids'] = [file_id, ]

        url = '%s/api/v3/teams/%s/channels/%s/posts/create' \
              % (self.server_url, self.team_id, self.channel_id)
        response = self.session.post(url, data=json.dumps(post_data))
        # f = open("out.txt", "wb")
        # f.write(response.request.body)
        # f.close()

        if response.status_code == 200:
            LOG.debug(response.content)
            post_id = response.json()["id"]
        else:
            raise RuntimeError(response.content)

        return post_id

    def get_post(self, post_id):
        """
        get a message from mattermost.
        :param post_id: message to retreive
        """
        LOG.debug("Getting message from mattermost: %s", post_id)
        url = '%s/api/v3/teams/%s/channels/%s/posts/%s/get' \
              % (self.server_url, self.team_id, self.channel_id, post_id)
        response = self.session.get(url)

        if response.status_code != 200:
            raise RuntimeError("Server unhappy. (%s)", response)

        return response.content

    def get_posts(self, offset=0, limit=10):
        """
        get messages from mattermost.
        """
        LOG.debug("Getting messages from mattermost")
        url = '%s/api/v3/teams/%s/channels/%s/posts/page/%d/%d' \
              % (self.server_url, self.team_id, self.channel_id, offset, limit)
        LOG.debug("Sending: %s", url)
        response = self.session.get(url)

        if response.status_code != 200:
            raise RuntimeError("Server unhappy. (%s)", response)

        return response.content

    def get_file(self, file_id):
        """
        geta file from mattermost.
        :param file_id: file to retreive
        """
        LOG.debug("Getting a file from mattermost")
        url = '%s/api/v3/files/%s/get' % (self.server_url, file_id)
        LOG.debug("Sending: %s", url)
        response = self.session.get(url)

        if response.status_code != 200:
            raise RuntimeError("Server unhappy. (%s)", response)

        return response.content


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

    if seconds > 0:
        timestring += '%ds' % seconds

    return timestring.strip()


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

if __name__ == '__main__':
    logging.basicConfig()
    LOG.setLevel(logging.DEBUG)

    conn = Mattermost(server_url="https://chat.avo.alaska.edu",
                      team_name='avo', channel_name='rs-processing-test')
    pid = conn.post("### Here's an image",
                    file_path="/Users/tomp/pytroll/satpy/ompstest.png")

    print("GOT POST %s" % pid)
    # conn.post("test2")
    # conn.post("test", file_path="/Users/tomp/pytroll/satpy/ompstest.png")
    # conn.get_post("h4yaamt1bby18f8pb1c864eqjc")
    # print(json.dumps(json.loads(conn.get_post("h4yaamt1bby18f8pb1c864eqjc")), indent=4))
    # print(json.dumps(conn.get_channels(conn.get_team_id('avo')), indent=4))
    # print("GOT TEAM %s" % conn.get_team_id('avo'))
    # print("GOT CHANNEL %s" % conn.get_channel_id(conn.get_team_id('avo'), "rs-processing-test"))
