#!/bin/bash

set -e
set -x

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    PYENV_ROOT="$HOME/.pyenv-simplejson"
    PATH="$PYENV_ROOT/bin:$PATH"
    hash -r
    eval "$(pyenv init -)"
fi

python -m compileall -f .
python setup.py pytest

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
  python setup.py bdist_wheel
fi
