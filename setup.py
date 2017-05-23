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
    url = "http://packages.python.org/tomputils",
    packages = find_packages(),
    long_description=open(join(dirname(__file__), 'README')).read(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Scientific/Engineering :: Visualization",
        "License :: OSI Approved :: BSD License",
    ],
    install_requires = [
        'requests',
        ],

)
