#!/usr/bin/env python3
#
# I waive copyright and related rights in the this work worldwide
# through the CC0 1.0 Universal public domain dedication.
# https://creativecommons.org/publicdomain/zero/1.0/legalcode
#
# Author(s):
#   Tom Parker <tparker@usgs.gov>

""" Watch config file for changes."""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import argparse
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


def _arg_parse():
    description = "I look after a config file."
    parser = argparse.ArgumentParser(description=description)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--url', help='URL of hosted config file')
    parser.add_argument("--user", help="Username")
    parser.add_argument("--passwd", help="password")
    parser.add_argument("config", help="Local config path")

    return parser.parse_args()


def download_config(args):
    try:
        r = requests.get(args.url, auth=(args.user, args.passwd))
        r.raise_for_status()
        return r.text
    except requests.exceptions.RequestException as e:
        logger.error("Cannot retrieve config file from %s", args.url)
        tutil.exit_with_error(e)


def update_svndir(config):
    logger.debug("Checking out svndir %s to %s", config['source'],
                 config['target'])

    r = svn.remote.RemoteClient(config['source'], username=config['user'],
                                password=config['passwd'])
    pathlib.Path(config['target']).mkdir(parents=True, exist_ok=True)
    r.checkout(config['target'])


def validate(config_file):
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
            logger.error("Configfile has changed.")
            logger.error("\n" + "".join(diff))
            shutil.copyfile(source, target)
        else:
            logger.info("Configfile has not changed.")
    except FileNotFoundError:
        logger.error("Container restarted, cannot verify config.")
        target_dir = os.path.dirname(target)
        pathlib.Path(target_dir).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def update_remotefile(config):
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


def bootstrap_config(args):
    bootstrap = {
        'name': 'bootstrap',
        'type': 'remotefile',
        'source': args.url,
        'target': CONFIG_PATH,
        'user': args.user,
        'passwd': args.passwd
    }
    update_config(bootstrap)

    return parse_config(CONFIG_PATH)


def main():
    # let ctrl-c work as it should.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    global logger
    logger = tutil.setup_logging("CONFIG FILE ERROR")
    args = _arg_parse()

    my_config = bootstrap_config(args)
    for config in my_config['configs']:
        config = update_config(config)

    logger.debug("That's all for now, bye.")
    logging.shutdown()


if __name__ == '__main__':
    main()
