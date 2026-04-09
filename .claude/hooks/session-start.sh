#!/bin/bash
set -euo pipefail

# Only run in remote (Claude Code on the web) environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Install Python versions and C build toolchain for _speedups.c development.
# The deadsnakes PPA provides Python 3.13, 3.14, and 3.14t (free-threaded).

# Add deadsnakes PPA if needed
if ! grep -q deadsnakes /etc/apt/sources.list.d/*.list 2>/dev/null; then
  sudo add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
fi

sudo apt-get update -qq 2>/dev/null

# Install Python versions with dev headers + GCC for C extension
sudo apt-get install -y -qq \
  gcc \
  python3.13 python3.13-dev \
  python3.14 python3.14-dev \
  python3.14-nogil libpython3.14-nogil \
  2>/dev/null

# Install setuptools/wheel for each Python
for py in python3.13 python3.14 python3.14t; do
  bin=$(which "$py" 2>/dev/null || true)
  if [ -n "$bin" ]; then
    "$bin" -m pip install --upgrade pip setuptools wheel 2>/dev/null || true
  fi
done

# Build C extension with Python 3.14
REQUIRE_SPEEDUPS=1 python3.14 setup.py build_ext -i 2>/dev/null || true
