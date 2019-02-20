#!/usr/bin/env python3
#
# I waive copyright and related rights in the this work worldwide
# through the CC0 1.0 Universal public domain dedication.
# https://creativecommons.org/publicdomain/zero/1.0/legalcode
#
# Author(s):
#   Tom Parker <tparker@usgs.gov>


"""
Keep an eye on a local config file, updating it when the upstream version
changes.

I will look to the environment for configuration, expecting to see the
following environmentvariables:

Required
    * CU_CONFIG_URL=http://example.com/path/to/config.yml

Optional
    * CU_USER=user
    * CU_PASSWORD=pass
    * CU_LOCAL_CONFIG=/path/to/config.yml
    * CU_CONTEXT_NAME=my context

"""


from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import logging
import signal
import requests
import os
import shutil
import errno
import pathlib

import tomputils.util as tutil
import ruamel.yaml
import difflib
import svn.remote


CONFIG_PATH = '/tmp/configupdater.yaml'


def update_svndir(config):
    """
    Update a config file stored in svn.

    Parameters
    ----------
    config : dict
        This files config stanza.
    """

    logger.debug("Checking out svndir %s to %s", config['source'],
                 config['target'])

    r = svn.remote.RemoteClient(config['source'], username=config['user'],
                                password=config['passwd'])
    pathlib.Path(config['target']).mkdir(parents=True, exist_ok=True)
    r.checkout(config['target'])


def validate(config_file):
    """
    Validate a YAML config file.

    Parameters
    ----------
    config_file : str
        Local path to config file.


    Returns
    -------
    Bool
        True if file contains valid YAML

    """
    if config_file.endswith('yaml'):
        try:
            yaml = ruamel.yaml.YAML()
            yaml.load(config_file)
        except ruamel.yaml.YAMLError as e1:
            logger.error("Cannot parse YAML config file")
            tutil.exit_with_error(e1)
    else:
        return True


def update_localfile(config):
    """
    Update a config file stored at a local path.

    Parameters
    ----------
    config : dict
        This files config stanza.
    """
    source = str(config['source'])
    target = str(config['target'])
    validate(source)
    try:
        with open(source, "r") as f:
            new_config = list(f)

        with open(target, "r") as f:
            current_config = list(f)

        result = difflib.unified_diff(current_config,
                                      new_config,
                                      fromfile=source,
                                      tofile=target)
        diff = list(result)
        if len(diff) > 0:
            logger.error("%s has changed.", target)
            logger.error("\n" + "".join(diff))
            shutil.copyfile(source, target)
        else:
            logger.info("%s has not changed.", target)
    except OSError as e:
        # do it this way to preserve Py2 compat
        if e.errno == errno.ENOENT:
            logger.error("Container restarted, cannot verify %s.", target)
            target_dir = os.path.dirname(target)
            pathlib.Path(target_dir).mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        else:
            raise


def update_remotefile(config):
    """
    Update a config file stored at a URL.

    Parameters
    ----------
    config : dict
        This files config stanza.
    """
    config_str = None
    try:
        r = requests.get(config['source'], auth=(config['user'],
                                                 config['passwd']))
        r.raise_for_status()

        config_str = r.text
    except requests.exceptions.RequestException as e:
        logger.error("Cannot retrieve config file from %s", config['url'])
        tutil.exit_with_error(e)

    tmp_config = '/tmp/config.tmp'
    with open(tmp_config, 'w') as f:
        f.write(config_str)

    config['type'] = 'localfile'
    config['source'] = tmp_config
    update_localfile(config)
    os.remove(tmp_config)


def update_config(config):
    """
    Update a monitored config file.

    Parameters
    ----------
    config : dict
        This files config stanza.
    """

    type = config['type']

    if type == 'svndir':
        update_svndir(config)
    elif type == 'localfile':
        update_localfile(config)
    elif type == 'remotefile':
        update_remotefile(config)
    else:
        logger.error("Unknown config type: %s", type)


def parse_config(config_path):
    """
    Parse my YAML config file.

    Parameters
    ----------
    config_path : str
        Path to my YAML config file.

    Returns
    -------
    Dict
        My configuration.
    """
    logger.debug("Parsing config %s", config_path)
    config_file = pathlib.Path(config_path)
    yaml = ruamel.yaml.YAML()
    config = None
    try:
        config = yaml.load(config_file)
    except ruamel.yaml.parser.ParserError as e1:
        logger.error("Cannot parse config file")
        tutil.exit_with_error(e1)
    except OSError as e:
        if e.errno == errno.EEXIST:
            logger.error("Cannot read config file %s", config_file)
            tutil.exit_with_error(e)
        else:
            raise

    return config


def bootstrap_config():
    """
    Retrieve and parse my config file.

    Returns
    -------
    Dict
        My configuration.
    """
    bootstrap = {
        'name': 'bootstrap',
        'type': 'remotefile',
        'source': tutil.get_env_var('CU_CONFIG_URL'),
        'target': tutil.get_env_var('CU_LOCAL_CONFIG', CONFIG_PATH),
        'user': tutil.get_env_var('CU_USER', None),
        'passwd': tutil.get_env_var('CU_PASSWORD', None, secret=True)
    }
    update_config(bootstrap)

    return parse_config(CONFIG_PATH)


def main():
    # let ctrl-c work as it should.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    global logger
    if 'CU_CONTEXT_NAME' in os.environ:
        context_name = os.environ['CU_CONTEXT_NAME']
        subject = "{} config file changed".format(context_name)
    else:
        subject = "Config file changed"

    logger = tutil.setup_logging(subject)

    my_config = bootstrap_config()
    for config in my_config['configs']:
        update_config(config)

    logger.debug("That's all for now, bye.")
    logging.shutdown()


if __name__ == '__main__':
    main()
