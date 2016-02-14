#!/bin/bash

set -e
set -x

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    if [ ! -e "$HOME/.pyenv" ]; then
      git clone https://github.com/yyuu/pyenv.git ~/.pyenv
    fi
    PYENV_ROOT="$HOME/.pyenv"
    PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"
    hash -r
    pyenv install --list
    pyenv install -s $PYENV_VERSION
    pip install wheel
fi
