# -*- coding: utf-8 -*-
"""
Provides a console interface for interactingwith a Mattermost server.

Required
    * MATTERMOST_USER_ID=mat_user
    * MATTERMOST_USER_PASS=mat_pass

Optional
    * MATTERMOST_SERVER_URL=https://chat.example.com
    * MATTERMOST_TEAM_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
    * MATTERMOST_CHANNEL_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx

"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import argparse
import json
import logging
import sys

from future.builtins import *  # NOQA

from .mattermost import DEFAULT_RETRIES, DEFAULT_TIMEOUT
from .mattermost import Mattermost

LOG = logging.getLogger(__name__)


def _arg_parse():
    description = "Interact with a Mattermost server. Not all possible " \
                  "combinations of arguments will make sense, avoid those " \
                  "that do not make sense. The message to post, if any, " \
                  "will be read from <STDIN>."

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("command", choices=('post', 'getteams', 'getchannels',
                                            'getposts'), help="Command")
    parser.add_argument("-a", "--attachments", action='append',
                        help="File to attach. Argument may be repeated to "
                             "attach multiple files.")
    parser.add_argument("-r", "--retries",
                        help="Maximum number of attemps to fulfill request",
                        type=int, default=DEFAULT_RETRIES)
    parser.add_argument("-t", "--timeout", help="request timeout", type=int,
                        default=DEFAULT_TIMEOUT)
    help_text = "Mattermost team name. Will override MATTERMOST_TEAM_ID " \
                + "environment variable."
    parser.add_argument("--team-name", help=help_text)
    help_text = "Mattermost channel name. Will override " \
                "MATTERMOST_CHANNEL_ID environment variable."
    parser.add_argument("--channel-name", help=help_text)
    parser.add_argument("-v", "--verbose", help="Verbose logging",
                        action='store_true')

    return parser.parse_args()


def do_command():
    """
    Fulfill a command provided on the command line. Entrypoint for mattermost
    console script.

    """
    logging.basicConfig()
    args = _arg_parse()
    if args.verbose is True:
        logging.getLogger().setLevel(logging.DEBUG)

    conn = Mattermost(retries=args.retries, timeout=args.timeout)
    if args.team_name is not None:
        conn.team_name(args.team_name)

    if args.channel_name is not None:
        conn.channel_name(args.channel_name)

    if args.command == 'post':
        LOG.debug("Executing post")
        message = sys.stdin.read()
        if len(message) > 0:
            conn.post(message, file_paths=args.attachments)
        else:
            LOG.error("I have no message to post.")
            sys.exit(1)
    elif args.command == 'getteams':
        print(json.dumps(conn.get_teams(), indent=4))
    elif args.command == 'getchannels':
        print(json.dumps(conn.get_channels(), indent=4))
    elif args.command == 'getposts':
        print(json.dumps(conn.get_posts(), indent=4))


if __name__ == '__main__':
    do_command()
