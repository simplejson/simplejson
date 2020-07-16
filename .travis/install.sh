#!/bin/bash

set -e
set -x

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    if [ ! -e "$HOME/.pyenv-simplejson/.git" ]; then
      if [ -e "$HOME/.pyenv-simplejson" ]; then
        rm -rf ~/.pyenv-simplejson
      fi
      git clone https://github.com/pyenv/pyenv.git ~/.pyenv-simplejson
    else
      (cd ~/.pyenv-simplejson; git pull)
    fi
    PYENV_ROOT="$HOME/.pyenv-simplejson"
    PATH="$PYENV_ROOT/bin:$PATH"
    hash -r
    eval "$(pyenv init -)"
    hash -r
    pyenv install --list
    pyenv install -s $PYENV_VERSION
    pip install wheel
fi

if [[ $BUILD_WHEEL == 'true' ]]; then
    pip install wheel cibuildwheel==1.5.2
fi
