#!/bin/sh

VERSION=`python -c "import tomputils; print(tomputils.__version__)"`
echo $VERSION
git add tomputils/__init__.py
git commit -m 'version bump'
git push \
&& git tag $VERSION \
&& git push --tags
