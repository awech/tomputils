# -*- coding: utf8 -*-
"""
Ship messages to server
"""
from io import StringIO
import logging
import os

import paramiko


def ship(queue):
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler())
    logging.getLogger().setLevel(logging.DEBUG)

    while True:
        filename = queue.get()
        (path, file) = os.path.split(filename)

        transport = paramiko.Transport((os.environ['WEB_HOST']))
        pkey = paramiko.RSAKey.from_private_key(
            StringIO(os.environ['PRIVATE_KEY'].replace('\\n', '\n')))
        user = os.environ['USER']
        transport.connect(pkey=pkey, username=user)
        sftp = paramiko.SFTPClient.from_transport(transport)
        remote_path = os.path.join(os.environ['WEB_PATH'],
                                   os.environ['HOSTNAME'], path)
        mkdir_p(sftp, remote_path)

        sftp.put(filename, file)
        sftp.close()
        transport.close()


def mkdir_p(sftp, remote_directory):
    """Change to this directory, recursively making new folders if needed.
    Returns True if any folders were created. Adapted from:
    https://stackoverflow.com/questions/14819681/#14819803
    """
    if remote_directory == '/':
        # absolute path so change directory to root
        sftp.chdir('/')
        return
    if remote_directory == '':
        # top-level relative directory must exist
        return
    try:
        sftp.chdir(remote_directory)  # sub-directory exists
    except IOError:
        dirname, basename = os.path.split(remote_directory.rstrip('/'))
        mkdir_p(sftp, dirname)  # make parent directories
        sftp.mkdir(basename)  # sub-directory missing, so created it
        sftp.chdir(basename)
        return True
