# -*- coding: utf-8 -*-
"""
Module for interacting with mattermost.
"""
import os
import json
import requests
import logging


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
        self.matterMostSession = requests.Session()
        self.matterMostSession.headers.update({"X-Requested-With": "XMLHttpRequest"})

        if 'SSL_CA' in os.environ:
            self.logger.debug("Using SSL key " + os.environ['SSL_CA'])
            self.matterMostSession.verify = os.environ['SSL_CA']

        url = self.server_url + '/api/v3/users/login'
        login_data = json.dumps({'login_id': self.user_id, 'password': self.user_pass})
        l = self.matterMostSession.post(url, data=login_data)
        self.logger.debug(l)
        # self.mattermostUserId = l.json()["id"]

    def get_teams(self):
        """
        Get a list of teams on the server.
        :return: 
        """
        p = self.matterMostSession.get('%s/api/v3/teams/all' % self.server_url)
        return(json.loads(p.content))

    def get_channels(self, team_id):
        """
        Get a list of available channels for a team
        :param team_id: 
        :return: 
        """
        p = self.matterMostSession.get('%s/api/v3/teams/%s/channels/' % (self.server_url, team_id))
        return(json.loads(p.content))

    def post(self, message):
        """
        post a message to mattermost
        :param message: 
        :return: 
        """
        """
        Post a message to Mattermost. Adapted from 
        http://stackoverflow.com/questions/42305599/how-to-send-file-through-mattermost-incoming-webhook
        :return: 
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
        r = self.matterMostSession.post(url, data=post_data)

        if r.status_code == 200:
            self.logger.debug(r.content)
        else:
            self.logger.warn(r.content)


def setup_logging(verbose):
    """
    Configure logging
    :param verbose: 
    :return: 
    """
    logger = logging.getLogger('Mattermost')
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Verbose logging")
    else:
        logging.getLogger().setLevel(logging.INFO)

    return logger


def format_timedelta(timedelta):
    """
    Format a timedelta into a human-friendly string
    :param timedelta: 
    :return: 
    """
    seconds = timedelta.total_seconds()

    days, r = divmod(seconds, 60 * 60 * 24)
    hours, r = divmod(r, 60 * 60)
    minutes, r = divmod(r, 60)
    seconds = r

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
    :param start: 
    :param end: 
    :return: 
    """
    time_string = start.strftime('%m/%d/%Y %H:%M:%S - ')
    time_string += end.strftime('%H:%M:%S')

    return time_string
