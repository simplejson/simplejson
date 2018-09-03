#!/bin/bash

set -e
set -x

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    PYENV_ROOT="$HOME/.pyenv-simplejson"
    PATH="$PYENV_ROOT/bin:$PATH"
    hash -r
    eval "$(pyenv init -)"
fi
REQUIRE_SPEEDUPS=1 python setup.py build_ext -i
python -m compileall -f .
python setup.py test

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    python setup.py bdist_wheel
fi

if [[ $BUILD_WHEEL == 'true' ]]; then
    cibuildwheel --output-dir dist
fi

if [[ $BUILD_SDIST == 'true' ]]; then
    python setup.py sdist
fi
