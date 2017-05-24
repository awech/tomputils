"""
tomputils -- Supporting modules.

tomputils is a collection of modules intended to support Tom's tools.
"""

from setuptools import setup, find_packages
from os.path import join, dirname
import tomputils

DOCSTRING = __doc__.split("\n")

setup(
    name = "tomputils",
    version = tomputils.__version__,
    author = "Tom Parker",
    author_email = "tparker@usgs.gov",
    description = (DOCSTRING[1]),
    license = "CC0",
    keywords = "mattermost",
    url = "http://github.com/tparker-usgs/tomputils",
    packages = find_packages(),
    long_description='\n'.join(DOCSTRING[3:]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Scientific/Engineering :: Visualization",
        "License :: OSI Approved :: BSD License",
    ],
    install_requires = [
        'requests',
        'future',
        ],

)
