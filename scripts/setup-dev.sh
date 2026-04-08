#!/bin/bash
# Setup script for simplejson development with multiple Python versions
# including free-threaded (nogil) builds for testing PEP 703 support.
#
# Usage: ./scripts/setup-dev.sh
#
# This installs Python 3.13, 3.14, and 3.14t (free-threaded) via the
# deadsnakes PPA, then builds the C extension for each and runs tests.

set -e

echo "=== Setting up simplejson development environment ==="

# Add deadsnakes PPA if not already present
if ! grep -q deadsnakes /etc/apt/sources.list.d/*.list 2>/dev/null; then
    echo "Adding deadsnakes PPA..."
    sudo add-apt-repository -y ppa:deadsnakes/ppa
fi

echo "Updating package lists..."
sudo apt-get update -qq

# Install Python versions and dev headers
echo "Installing Python versions..."
sudo apt-get install -y -qq \
    python3.13 python3.13-dev \
    python3.14 python3.14-dev \
    python3.14-nogil libpython3.14-nogil

echo ""
echo "=== Installed Python versions ==="
for py in python3.13 python3.14 python3.14t; do
    bin=$(which "$py" 2>/dev/null || true)
    if [ -n "$bin" ]; then
        echo "  $py: $($bin --version 2>&1)"
    else
        echo "  $py: not found"
    fi
done

echo ""
echo "=== Building and testing C extension ==="

# Build and test with each available Python
for py in python3.13 python3.14 python3.14t; do
    bin=$(which "$py" 2>/dev/null || true)
    if [ -z "$bin" ]; then
        echo "--- $py: skipped (not found) ---"
        continue
    fi

    echo ""
    echo "--- $py ($($bin --version 2>&1)) ---"

    echo "  Building extension..."
    if ! REQUIRE_SPEEDUPS=1 "$bin" setup.py build_ext -i 2>&1 | tail -3; then
        echo "  BUILD FAILED"
        continue
    fi

    echo "  Running tests..."
    if "$bin" -m simplejson.tests._cibw_runner . 2>&1 | tail -3; then
        echo "  PASSED"
    else
        echo "  TESTS FAILED"
    fi

    # For free-threaded Python, also test with GIL disabled
    if [ "$py" = "python3.14t" ]; then
        echo "  Verifying GIL-free import..."
        if PYTHON_GIL=0 "$bin" -W error::RuntimeWarning -c "import simplejson._speedups" 2>&1; then
            echo "  GIL-free import OK"
        else
            echo "  GIL-free import FAILED"
        fi

        echo "  Running tests with GIL disabled..."
        if PYTHON_GIL=0 "$bin" -m simplejson.tests._cibw_runner . 2>&1 | tail -3; then
            echo "  PASSED (GIL disabled)"
        else
            echo "  TESTS FAILED (GIL disabled)"
        fi
    fi
done

echo ""
echo "=== Setup complete ==="
echo ""
echo "Quick reference:"
echo "  Build extension:   python3.14t setup.py build_ext -i"
echo "  Run tests:         python3.14t -m simplejson.tests._cibw_runner ."
echo "  Test GIL-free:     PYTHON_GIL=0 python3.14t -W error::RuntimeWarning -c 'import simplejson._speedups'"
echo "  Test w/o GIL:      PYTHON_GIL=0 python3.14t -m simplejson.tests._cibw_runner ."
