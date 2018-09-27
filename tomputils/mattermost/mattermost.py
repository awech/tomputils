# -*- coding: utf-8 -*-
"""
Interact with a Mattermost server.

This modules ineracts with a `Mattermost <http://mattermost.com/>`_ server
using `Mattermost API V4 <https://api.mattermost.com/>`_. It will look to the
environment for configuration, expecting to see the following environment
variables:

Required
    * MATTERMOST_USER_ID=mat_user
    * MATTERMOST_USER_PASS=mat_pass

Optional
    * MATTERMOST_SERVER_URL=https://chat.example.com
    * MATTERMOST_TEAM_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
    * MATTERMOST_CHANNEL_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
    * SSL_CA=/path/to/cert

"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import json
import logging
import os
from future.builtins import *  # NOQA

import requests
import requests.exceptions
import OpenSSL.SSL

LOG = logging.getLogger(__name__)
MAX_ATTACHMENTS = 5
DEFAULT_RETRIES = 5
DEFAULT_TIMEOUT = 15


class Mattermost(object):
    """
    Interact with a mattermost server.

    Parameters
    ----------
    server_url : str, optional
        URL of Mattermost server. Optional if MATTERMOST_SERVER_URL
        environment variable is present.
    timeout : int or tuple of (int, int), optional
        HTTP timeout.
    retries : int, optional
        Number of times to retry a request.

    Attributes
    ----------
    timeout : int or tuple of (int, int)
        HTTP timeout.
    retries : int
        Maximum number of times to send a request to the Mattermost server.
    team_id : str
        Mattermost ID of the working team
    channel_id : str
        Mattermost ID of the working channel
    server_url : str
        URL of Mattermost server

    Examples
    --------
    >>> import json
    >>> import tomputils.mattermost as mm
    >>> conn = mm.Mattermost()
    >>> print(json.dumps(conn.get_teams(), indent=4))
    [
        {
            "allowed_domains": "",
            "display_name": "AVO",
            "name": "avo",
            "invite_id": "89hj448uktds989hj448uktds9",
            "delete_at": 0,
            "update_at": 1488239656296,
            "create_at": 1487379468267,
            "email": "mmadmin@example.com",
            "company_name": "",
            "allow_open_invite": true,
            "type": "O",
            "id": "39ou1iab7pnom39ou1iab7pnom",
            "description": ""
        }
    ]
    >>>

    """

    def __init__(self, server_url=None, timeout=DEFAULT_TIMEOUT,
                 retries=DEFAULT_RETRIES):
        try:
            self._user_id = os.environ['MATTERMOST_USER_ID']
            self._user_pass = os.environ['MATTERMOST_USER_PASS']
        except KeyError:
            raise RuntimeError("MATTERMOST_USER_ID and MATTERMOST_USER_PASS "
                               "environment variables must be set.")

        if server_url is not None:
            self.server_url = server_url
        elif 'MATTERMOST_SERVER_URL' in os.environ:
            self.server_url = os.environ['MATTERMOST_SERVER_URL']
        else:
            raise RuntimeError("Server URL must be provided in environment"
                               " or passed to the constructor.")
        LOG.debug("Mattermost server URL: %s", self.server_url)

        if 'MATTERMOST_TEAM_ID' in os.environ:
            self.team_id = os.environ['MATTERMOST_TEAM_ID']
        else:
            self.team_id = None
        LOG.debug("Mattermost team id: %s", self.team_id)

        if 'MATTERMOST_CHANNEL_ID' in os.environ:
            self.channel_id = os.environ['MATTERMOST_CHANNEL_ID']
        else:
            self.channel_id = None
        LOG.debug("Mattermost channel id: %s", self.channel_id)

        self.timeout = timeout
        LOG.debug("timeout: %s", self.timeout)

        self.retries = retries
        LOG.debug("retries: %s", self.retries)

        self._session = requests.Session()
        self._session.headers.update({"X-Requested-With": "XMLHttpRequest"})
        # if 'SSL_CA' in os.environ:
        #     LOG.debug("Using SSL key %s", os.environ['SSL_CA'])
        #     self._session.verify = os.environ['SSL_CA']

        self._login()

    def post(self, message, file_paths=None):
        """
        Post a message to mattermost.

        Adapted from http://stackoverflow.com/questions/42305599/\
        how-to-send-file-through-mattermost-incoming-webhook

        Parameters
        ----------
        message : str
            Message text to be posted.

        file_paths : str or list of str, optional
            Files to be attached to post.

        Returns
        -------
        str
            Mattermost ID of the post.

        """
        LOG.debug("Posting message to mattermost: %s", message)
        post_data = {
            'channel_id': self.channel_id,
            'message': message,
        }

        if file_paths is not None:
            if not isinstance(file_paths, list):
                file_paths = [file_paths]

            file_count = len(file_paths)
            if file_count > MAX_ATTACHMENTS:
                raise RuntimeError("Matter most supports no more than %d "
                                   "attachments per post, but %d attachemnts "
                                   "provided." % (MAX_ATTACHMENTS, file_count))
            file_ids = []
            for file_path in file_paths:
                LOG.debug("attaching file: %s", file_path)
                file_ids.append(self.upload(file_path))
            post_data['file_ids'] = file_ids

        url = '%s/api/v4/posts' % self.server_url
        response = self._request(self._session.post, url,
                                 data=json.dumps(post_data))

        if response.status_code == 201:
            LOG.debug(response.content)
            post_id = response.json()["id"]
        else:
            raise RuntimeError(response.content)

        return post_id

    def team_name(self, team_name):
        """
        Set team ID given a name.

        Parameters
        ----------
        team_name : str
            Name of team to find.

        """
        self.team_id = self.get_team_id(team_name)
        LOG.debug("Mattermost team id: %s", self.team_id)

    def channel_name(self, channel_name):
        """
        Set channel ID given a name.

        Parameters
        ----------
        channel_name : str
            Name of channel to find.

        """
        self.channel_id = self.get_channel_id(channel_name)
        LOG.debug("Mattermost channel id: %s", self.channel_id)

    def _request(self, method, url, retries=None, **kwargs):
        """
        Make a HTTP request, retrying if necessary.

        Parameters
        ----------
        method : bound method
            Method used to make the request.
        url : unicode or str
        retries : int, optional

        Returns
        -------
        json
            Server response.

        """
        if retries is None:
            retries = self.retries

        try:
            LOG.debug("Attempting: %s %s", method, kwargs)
            if 'SSL_CA' in os.environ:
                return method(url, verify=os.environ['SSL_CA'], **kwargs)
            else:
                return method(url, **kwargs)
        except (requests.exceptions.SSLError, OpenSSL.SSL.Error):
            if 'SSL_CA' in os.environ:
                LOG.info("SSL verification failed, trying default certs.")
                return method(url, **kwargs)
            else:
                LOG.error("SSL verification failed.")
                raise
        except Exception:
            if retries > 0:
                self._request(method, url, retries=retries-1, **kwargs)
            else:
                raise

    def _login(self):
        """
        Authenticate with the server.

        """
        url = self.server_url + '/api/v4/users/login'
        login_data = json.dumps({'login_id': self._user_id,
                                 'password': self._user_pass})
        LOG.debug("Sending: %s", login_data)
        response = self._request(self._session.post, url, data=login_data)
        LOG.debug("Received: %s", response.json())

        if response.status_code != 200:
            raise RuntimeError("Cannot login. Server reported: %s"
                               % response.content)

    def get_teams(self):
        """
        Get a list of teams on the server.

        Returns
        -------
        JSON
            Teams on server

        Examples
        --------
        >>> import json
        >>> import tomputils.mattermost as mm
        >>> conn = mm.Mattermost()
        >>> print(json.dumps(conn.get_teams(), indent=4))
        [
            {
                "allowed_domains": "",
                "display_name": "AVO",
                "name": "avo",
                "invite_id": "89hj448uktds989hj448uktds9",
                "delete_at": 0,
                "update_at": 1488239656296,
                "create_at": 1487379468267,
                "email": "mmadmin@example.com",
                "company_name": "",
                "allow_open_invite": true,
                "type": "O",
                "id": "39ou1iab7pnom39ou1iab7pnom",
                "description": ""
            }
        ]

        """
        url = '{}/api/v4/teams'.format(self.server_url)
        response = self._request(self._session.get, url)
        return json.loads(response.content)

    def get_team_id(self, team_name):
        """
        Get a team id, given its name.

        Parameters
        ----------
        team_name : str
            Name of team to find.

        Returns
        -------
        str
            Mattermost team ID.

        """

        teams = self.get_teams()
        for team in teams:
            if team['name'] == team_name:
                return team['id']

        return None

    def get_channels(self, page=0, per_page=60):
        """
        Get a list of public channels.

        Parameters
        ----------
        page : int, optional
            Which page to return.

        per_page : int, optional
            Number of channels per page.

        Returns
        -------
        JSON
            Available channels.

        Examples
        --------
        >>> import json
        >>> import tomputils.mattermost as mm
        >>> conn = mm.Mattermost()
        >>> print(json.dumps(conn.get_channels(), indent=4))
        [
        {
                "extra_update_at": 1527181740217,
                "total_msg_count": 83,
                "display_name": "Town Square",
                "name": "town-square",
                "delete_at": 0,
                "update_at": 1525543855322,
                "create_at": 1525543855322,
                "header": "",
                "team_id": "68hykcaoti8zfmjadmf28fnxba",
                "purpose": "",
                "creator_id": "",
                "last_post_at": 1527181740220,
                "type": "O",
                "id": "93gzrbcp48shw2ngtbd79so4oo"
        }
        ]

        """
        if self.team_id is None:
            raise RuntimeError("Please set team_id before calling"
                               "get_channels")
        url = '{}/api/v4/teams/{}/channels?page={}&per_page={}'
        url = url.format(self.server_url, self.team_id, page, per_page)
        response = self._request(self._session.get, url)
        return json.loads(response.content)

    def get_channel_id(self, channel_name):
        """
        Return channel id given a channel name.

        Parameters
        ----------
        channel_name : str

        Returns
        -------
        str
            Mattermost ID of channel.
        """
        if self.team_id is None:
            raise RuntimeError("Please set team_id before calling"
                               "get_channel_id")
        channels = []
        i = 0
        ch = self.get_channels()
        while ch:
            channels.extend(ch)
            i += 1
            ch = self.get_channels(page=i)
        for channel in channels:
            if channel['name'] == channel_name:
                return channel['id']

        return None

    def get_team_stats(self):
        """
        Return stats for a specific team.

        Returns
        -------
        JSON
            User stats for a team.
        """
        if self.team_id is None:
            raise RuntimeError("Please set team_id before calling"
                               "get_team_stats")
        url = '%s/api/v4/teams/%s/stats' % (self.server_url, self.team_id)
        response = self._request(self._session.get, url)
        return json.loads(response.content)

    def get_team_users(self, page=0, per_page=60):
        """
        Get a list of users on the given team.

        Parameters
        ----------
        page : int, optional
            Which page to return.

        per_page : int, optional
            Number of users per page.

        Returns
        -------
        JSON
            Users on team

        Examples
        --------
        >>> import json
        >>> import tomputils.mattermost as mm
        >>> conn = mm.Mattermost()
        >>> print(json.dumps(conn.get_users(), indent=4))
        [
            {
                "username": "auser",
                "first_name": "",
                "last_name": "",
                "roles": "system_user",
                "locale": "en",
                "delete_at": 0,
                "update_at": 1526962598413,
                "create_at": 1526516730888,
                "auth_service": "",
                "email": "mail@example.com",
                "auth_data": "",
                "position": "",
                "nickname": "",
                "id": "dz1icdoalvn571r19yk6wx8tur"
            }
        ]

        """
        url = '%s/api/v4/users?in_team=%s&page=%d&per_page=%d' \
              % (self.server_url, self.team_id, page, per_page)
        response = self._request(self._session.get, url)
        return json.loads(response.content)

    def upload(self, file_path):
        """
        Upload a file which can later be attached to a post.

        Parameters
        ----------
        file_path : str

        Returns
        -------
        str
            Mattermost ID of uploaded file.

        """
        LOG.debug(("Uploading file to mattermost: %s", file_path))
        filename = os.path.basename(file_path)
        post_data = {'channel_id': self.channel_id,
                     'client_ids': filename}
        file_data = {'files': (filename, open(file_path, 'rb'))}
        url = '%s/api/v4/files' % self.server_url
        response = self._request(self._session.post, url, data=post_data,
                                 files=file_data)
        LOG.debug("Received: %s - %s", response.status_code, response.text)

        if response.status_code != 201:
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

    def get_post(self, post_id):
        """
        Get a message from mattermost, given its id.

        Parameters
        ----------
        post_id: str
            Mattermost ID of the post to be retreived.

        Returns
        -------
        json
            JSON of the post.

        """
        LOG.debug("Getting message from mattermost: %s", post_id)
        url = '%s/api/v4/posts/%s' % (self.server_url, post_id)
        response = self._request(self._session.get, url)

        if response.status_code != 200:
            raise RuntimeError("Server unhappy. (%s)", response)

        return response.content

    def get_posts(self, page=0, per_page=30, since=0):
        """
        Get a series of posts from a Mattermost channel.

        Parameters
        ----------
        page : int, optional
            The page to select
        per_page : int, optional
            Number of posts per page
        since : int, optional
            Unix timestamp listing start of posts to return

        Returns
        -------
        json
            JSON containing the posts.

        """
        LOG.debug("Getting messages from mattermost")
        url = '%s/api/v4/channels/%s/posts?page=%d&per_page=%d&since=%d' \
              % (self.server_url, self.channel_id, page, per_page, since)
        LOG.debug("Sending: %s", url)
        response = self._request(self._session.get, url)

        if response.status_code != 200:
            raise RuntimeError("Server unhappy. (%s)", response)

        return response.content

    def get_file(self, file_id):
        """
        Get a file from mattermost, given its id.

        Parameters
        ----------
        file_id: str
            Mattermost id of the file to be retreived.

        Returns
        -------
        bytes
            File bytes.

        """
        LOG.debug("Getting a file from mattermost")
        url = '%s/api/v4/files/%s' % (self.server_url, file_id)
        LOG.debug("Sending: %s", url)
        response = self._request(self._session.get, url)

        if response.status_code != 200:
            raise RuntimeError("Server unhappy. (%s)", response)

        return response.content

    def get_attachment_info(self, att_id):
        """
        Get metadata for a post attachment.

        Parameters
        ----------
        att_id: str
            Id of the attachment to retrieve info about.

        Returns
        -------
        json
            Attachment metadata in json format.

        """
        LOG.debug("Getting info for an attachment from mattermost")
        url = '%s/api/v4/files/%s/info' % (self.server_url, att_id)
        LOG.debug("Sending: %s", url)
        response = self._request(self._session.get, url)

        if response.status_code != 200:
            raise RuntimeError("Server unhappy. (%s)", response)

        return response.content


def format_timedelta(timedelta):
    """
    Format a timedelta into a human-friendly string.

    Parameters
    ----------
    timedelta : timedelta

    Returns
    -------
    str
        Formatted timedelta.

    Examples
    --------
    >>> from datetime import timedelta
    >>> from tomputils import mattermost as mm
    >>> td = timedelta(days=2, hours=4, seconds=5)
    >>> print(mm.format_timedelta(td))
    2d 4h 5s
    >>>

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
    Format a time span into a human-friendly string.

    Parameters
    ----------
    start : datetime
    end : datetime

    Returns
    -------
    str
        Formatted time span.

    Examples
    --------
    >>> from datetime import datetime
    >>> from tomputils import mattermost as mm
    >>> start = datetime(2017,4,1,12,55,1)
    >>> end = datetime(2017,4,2,2,20,1)
    >>> print(mm.format_span(start, end))
    04/01/2017 12:55:01 - 02:20:01
    >>>

    """
    time_string = start.strftime('%m/%d/%Y %H:%M:%S - ')
    time_string += end.strftime('%H:%M:%S')

    return time_string
