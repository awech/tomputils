#!/bin/sh

rm -fr dist build
python setup.py bdist_wheel
twine upload dist/*
