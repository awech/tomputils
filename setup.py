"""
tomputils -- Supporting modules.

tomputils is a collection of modules intended to support Tom's tools.
"""

from setuptools import setup, find_packages
import tomputils

DOCSTRING = __doc__.split("\n")

setup(
    name="tomputils",
    version=tomputils.__version__,
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
    install_requires=[
        'requests',
        'future',
        'pycurl'
        ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mattermost = tomputils.mattermost.mattermost_console:do_command',
            'downloader = tomputils.downloader.downloader_console:do_command'
        ]
    }
)
