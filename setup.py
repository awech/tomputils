"""
tomputils -- Supporting modules.

tomputils is a collection of modules intended to support Tom's tools.
"""

from setuptools import setup, find_packages
from tomputils import __version__

DOCSTRING = __doc__.split("\n")

setup(
    name="tomputils",
    version=__version__,
    author="Tom Parker",
    author_email="tparker@usgs.gov",
    description=(DOCSTRING[1]),
    license="CC0",
    keywords="mattermost",
    url="http://github.com/tparker-usgs/tomputils",
    packages=find_packages(),
    long_description='\n'.join(DOCSTRING[3:]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Software Development :: Libraries",
        "License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication",
    ],
    dependency_links=[
        'https://github.com/tparker-usgs/py-single/tarball/py3#egg=single-1.0.0'
    ],
    install_requires=[
        'requests',
        'future',
        'pika',
        'pycurl',
        'pyOpenSSL',
        'buffering_smtp_handler',
        'svn',
        'ruamel.yaml'
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    scripts=['bin/singleTimeout.sh'],
    entry_points={
        'console_scripts': [
            'mattermost = tomputils.mattermost.mattermost_console:do_command',
            'downloader = tomputils.downloader.downloader_console:download',
            'configupdater = tomputils.configupdater.configupdater_console:main'
        ]
    }
)
