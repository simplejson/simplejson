#!/usr/bin/env bash
# Build a TSan-instrumented free-threaded CPython (if needed) and run the
# simplejson stress test under it. Re-runs are cheap: clone, build, and
# install are skipped when artifacts are already present.
#
# Intended for local use and future CI integration. In CI, cache
# ${TSAN_ROOT} keyed on ${CPYTHON_REF} to skip the CPython rebuild.
#
# Required build deps (Debian/Ubuntu):
#   apt install -y build-essential git libssl-dev zlib1g-dev libbz2-dev \
#                  libreadline-dev libsqlite3-dev libffi-dev liblzma-dev

set -euo pipefail

: "${CPYTHON_REF:=v3.14.0}"
: "${CPYTHON_REPO:=https://github.com/python/cpython.git}"
: "${TSAN_ROOT:=${HOME}/.cache/py-tsan-ft}"
: "${TSAN_OPTIONS:=halt_on_error=0 second_deadlock_stack=1 history_size=7 handle_segv=0}"

# TSan's shadow-memory layout expects PIE binaries to land in a narrow range.
# Modern Linux kernels (>=5.x) randomize mmap widely enough that sanitizer-
# instrumented programs (including CPython's build-time _freeze_module helper)
# crash with "unexpected memory mapping". Disabling ASLR for the process with
# setarch -R (ADDR_NO_RANDOMIZE personality, no root needed) sidesteps this.
NO_ASLR=(setarch "$(uname -m)" -R)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
: "${SIMPLEJSON_ROOT:=$(cd "${SCRIPT_DIR}/.." && pwd)}"
: "${STRESS_SCRIPT:=${SIMPLEJSON_ROOT}/tsan_stress_simplejson.py}"
: "${REPORT:=${SIMPLEJSON_ROOT}/tsan_report.txt}"

TSAN_SRC="${TSAN_ROOT}/src-${CPYTHON_REF}"
TSAN_PREFIX="${TSAN_ROOT}/install-${CPYTHON_REF}"
PY="${TSAN_PREFIX}/bin/python3"

log() { printf '==> %s\n' "$*"; }

ensure_source() {
    if [[ -d "${TSAN_SRC}/.git" ]]; then
        log "cpython source present at ${TSAN_SRC}"
        return
    fi
    log "cloning ${CPYTHON_REPO}@${CPYTHON_REF} -> ${TSAN_SRC}"
    mkdir -p "${TSAN_ROOT}"
    git clone --depth 1 --branch "${CPYTHON_REF}" "${CPYTHON_REPO}" "${TSAN_SRC}"
}

python_is_tsan_ft() {
    [[ -x "${PY}" ]] || return 1
    "${PY}" - <<'PY' >/dev/null 2>&1 || return 1
import sys, sysconfig
gil = sysconfig.get_config_var('Py_GIL_DISABLED')
cflags = sysconfig.get_config_var('CFLAGS') or ''
assert gil == 1, f'Py_GIL_DISABLED={gil!r}'
assert '-fsanitize=thread' in cflags, f'no -fsanitize=thread in CFLAGS'
PY
}

build_cpython() {
    if python_is_tsan_ft; then
        log "tsan free-threaded python already built at ${PY}"
        return
    fi
    # A previous failed build leaves .o files compiled with a different CC;
    # make clean ensures the rebuild is consistent with the chosen compiler.
    if [[ -f "${TSAN_SRC}/Makefile" ]]; then
        log "cleaning previous build artifacts in ${TSAN_SRC}"
        (cd "${TSAN_SRC}" && make -s distclean 2>/dev/null || true)
    fi
    log "configuring CPython (--disable-gil --with-thread-sanitizer)"
    local jobs
    jobs=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
    # CPython's own TSan CI uses clang; gcc's TSan mishandles CPython's
    # frozen getpath (corrupted wchar_t decode at startup). Prefer clang
    # when available and fall back to the default compiler otherwise.
    local cc_args=()
    if command -v clang >/dev/null 2>&1; then
        cc_args=(CC=clang CXX=clang++)
        log "using clang for TSan build"
    else
        log "WARNING: clang not found; falling back to default CC (expect frozen-getpath crash with gcc)"
    fi
    (
        cd "${TSAN_SRC}"
        # Several configure AC_RUN_IFELSE tests fail under -fsanitize=thread
        # because the sanitizer runtime isn't linked into the tiny test
        # programs. Preset the autoconf cache vars so configure trusts the
        # test result instead of executing the binary.
        ac_cv_buggy_getaddrinfo=no \
        ac_cv_strftime_c99_support=yes \
        ./configure \
            "${cc_args[@]}" \
            --disable-gil \
            --with-thread-sanitizer \
            --prefix="${TSAN_PREFIX}"
        log "building (make -j${jobs})"
        "${NO_ASLR[@]}" make -j"${jobs}"
        log "installing -> ${TSAN_PREFIX}"
        "${NO_ASLR[@]}" make install
    )
    "${NO_ASLR[@]}" "${PY}" -m ensurepip --upgrade
    "${NO_ASLR[@]}" "${PY}" -m pip install --upgrade pip setuptools wheel
}

install_simplejson() {
    log "installing simplejson (editable) into ${TSAN_PREFIX}"
    REQUIRE_SPEEDUPS=1 "${NO_ASLR[@]}" "${PY}" -m pip install --no-build-isolation -e "${SIMPLEJSON_ROOT}"
    "${NO_ASLR[@]}" "${PY}" -c 'from simplejson._speedups import make_scanner, make_encoder; print("speedups loaded")'
}

run_stress() {
    log "running stress test -> ${REPORT}"
    : > "${REPORT}"
    PYTHON_GIL=0 TSAN_OPTIONS="${TSAN_OPTIONS}" \
        "${NO_ASLR[@]}" "${PY}" "${STRESS_SCRIPT}" 2> "${REPORT}" || true
    if grep -q 'WARNING: ThreadSanitizer' "${REPORT}"; then
        local count
        count=$(grep -c 'WARNING: ThreadSanitizer' "${REPORT}")
        log "tsan detected ${count} warning(s) - see ${REPORT}"
        exit 1
    fi
    log "no tsan warnings"
}

PHASE="${1:-all}"
case "${PHASE}" in
    build)
        ensure_source
        build_cpython
        ;;
    test)
        install_simplejson
        run_stress
        ;;
    all)
        ensure_source
        build_cpython
        install_simplejson
        run_stress
        ;;
    *)
        echo "usage: $0 [build|test|all]" >&2
        exit 2
        ;;
esac
