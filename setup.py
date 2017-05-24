from setuptools import setup, find_packages
from os.path import join, dirname
import tomputils

setup(
    name = "tomputils",
    version = tomputils.__version__,
    author = "Tom Parker",
    author_email = "tparker@usgs.gov",
    description = ("A collection of supporting utilities."),
    license = "CC0",
    keywords = "mattermost",
    packages = find_packages(),
    long_description=open(join(dirname(__file__), 'README')).read(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Software Development :: Libraries",
        "License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication",
    ],
    install_requires = [
        'requests',
        ],

)
