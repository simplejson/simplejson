#!/usr/bin/env python3
"""TSan stress test for simplejson._speedups.

================================================================================
Building a TSan + free-threaded CPython (one-time)
================================================================================
    git clone https://github.com/python/cpython.git cpython-tsan
    cd cpython-tsan
    ./configure --disable-gil --with-thread-sanitizer \
                --prefix=$HOME/py-tsan-ft
    make -j$(nproc) && make install
    $HOME/py-tsan-ft/bin/python3 -m pip install -e /home/bob/src/simplejson

================================================================================
Running this script under TSan
================================================================================
    cd /home/bob/src/simplejson
    PYTHON_GIL=0 \
      TSAN_OPTIONS='halt_on_error=0 second_deadlock_stack=1 history_size=7' \
      $HOME/py-tsan-ft/bin/python3 tsan_stress_simplejson.py \
      2> tsan_report.txt

    # Triage:
    /ft-review-toolkit:explore . tsan tsan_report.txt

================================================================================
Configuration (environment variables)
================================================================================
    TSAN_THREADS     concurrent workers (default: cpu_count or 8)
    TSAN_ITERATIONS  calls per worker per scenario (default 2000; auto-lowered
                     on TSan builds)
    TSAN_DURATION    approximate wall-clock seconds per scenario (default 2.5)
    TSAN_TIMEOUT     per-scenario hard timeout in seconds (default 60)

What this exercises
-------------------
  - Scenario 1: N threads share ONE make_scanner() instance; each parses
    different-but-overlapping JSON (dict/list/string cases). Targets scanner
    s->memo (PyDict_SetItem/Clear) under concurrent scan_once().
  - Scenario 2: N threads share ONE make_encoder() instance; each encodes
    distinct nested dict/list objects. Targets self->markers and
    self->key_memo mutation on concurrent calls.
  - Scenario 3: N threads encode the SAME shared dict. Stresses the
    Py_BEGIN_CRITICAL_SECTION(dct) path in encoder_listencode_dict.
  - Scenario 4: N threads encode the SAME shared list. Stresses the
    Py_BEGIN_CRITICAL_SECTION(seq) path in encoder_listencode_list.
  - Scenario 5: Mutator thread adds/removes keys while N readers encode the
    same dict (read-write contention on the input container).
  - Scenario 6: Module-level hammer for scanstring + encode_basestring_ascii.
"""
import os
import signal
import sys
import threading
import time
import warnings

warnings.filterwarnings("ignore", ".*GIL.*")


# --------------------------- configuration ---------------------------------- #

def _env_int(name, default):
    try:
        v = os.environ.get(name)
        return int(v) if v else default
    except ValueError:
        return default


def _env_float(name, default):
    try:
        v = os.environ.get(name)
        return float(v) if v else default
    except ValueError:
        return default


def _is_tsan_build():
    try:
        import sysconfig
        cflags = (sysconfig.get_config_var("CFLAGS") or "").lower()
        ldflags = (sysconfig.get_config_var("LDFLAGS") or "").lower()
        return "fsanitize=thread" in cflags or "fsanitize=thread" in ldflags
    except Exception:
        return False


THREADS = _env_int("TSAN_THREADS", os.cpu_count() or 8)
ITERATIONS = _env_int("TSAN_ITERATIONS", 2000)
DURATION = _env_float("TSAN_DURATION", 2.5)
SCENARIO_TIMEOUT = _env_int("TSAN_TIMEOUT", 60)

if _is_tsan_build():
    # TSan finds races on first occurrence; cap work to keep runtime sane.
    THREADS = min(THREADS, 6)
    ITERATIONS = min(ITERATIONS, 400)


# --------------------------- import guard ----------------------------------- #

try:
    from simplejson import _speedups
except ImportError as exc:
    print(f"SKIP: cannot import simplejson._speedups: {exc}", file=sys.stderr)
    sys.exit(0)

missing = [
    n for n in ("make_scanner", "make_encoder",
                "encode_basestring_ascii", "scanstring")
    if not hasattr(_speedups, n)
]
if missing:
    print(f"SKIP: simplejson._speedups missing symbols: {missing}",
          file=sys.stderr)
    sys.exit(0)


# --------------------------- shared fixtures -------------------------------- #

# A minimal context object that satisfies the fields read by make_scanner().
# Mirrors simplejson.scanner.JSONDecoder attributes accessed in Scanner init.
import decimal


class _ScanCtx:
    __slots__ = (
        "encoding", "strict", "object_hook", "object_pairs_hook",
        "array_hook", "parse_float", "parse_int", "parse_constant", "memo",
    )

    def __init__(self):
        self.encoding = "utf-8"
        self.strict = True
        self.object_hook = None
        self.object_pairs_hook = None
        self.array_hook = None
        self.parse_float = float
        self.parse_int = int
        self.parse_constant = float
        self.memo = {}


def _make_shared_scanner():
    return _speedups.make_scanner(_ScanCtx())


def _make_shared_encoder():
    # Matches the argument order in simplejson/encoder.py c_make_encoder call.
    markers = {}
    key_memo = {}
    return _speedups.make_encoder(
        markers,                            # markers (cycle detection)
        lambda o: str(o),                   # default
        _speedups.encode_basestring_ascii,  # _encoder (ascii)
        None,                               # indent
        ": ", ", ",                         # key_sep, item_sep
        False,                              # sort_keys
        False,                              # skipkeys
        True,                               # allow_nan
        key_memo,                           # key_memo
        False,                              # use_decimal
        False,                              # namedtuple_as_object
        True,                               # tuple_as_array
        None,                               # int_as_string_bitcount (None or positive int)
        None,                               # item_sort_key
        "utf-8",                            # encoding
        False,                              # for_json
        False,                              # ignore_nan
        decimal.Decimal,                    # Decimal
        False,                              # iterable_as_array
    )


# Varied JSON documents exercising dict / list / string / number / escapes.
JSON_SAMPLES = [
    b'{"a": 1, "b": [1,2,3], "c": "hello"}',
    b'[1, 2, 3, 4, "five", null, true, false]',
    b'{"nested": {"x": [1, {"y": [2, {"z": 3}]}]}}',
    b'"a plain \\"quoted\\" string with \\u00e9 escapes and \\n newlines"',
    b'{"k1":"v1","k2":"v2","k3":"v3","k4":"v4","k5":"v5"}',
    b'[{"id":1,"name":"alice"},{"id":2,"name":"bob"},{"id":3,"name":"carol"}]',
    b'{"a":1,"b":2,"c":3,"d":4,"e":5,"f":6,"g":7,"h":8}',
    b'{"list":[1.5, 2.5, 3.5, -0.25, 1e10, -2.3e-5]}',
]
JSON_SAMPLES = [s.decode("utf-8") for s in JSON_SAMPLES]


def _make_distinct_object(i):
    return {
        "id": i,
        "name": f"item-{i}",
        "tags": ["alpha", "beta", "gamma", f"n{i}"],
        "nested": {"x": i, "y": [i, i + 1, i + 2], "s": "x" * (i % 16)},
        "vals": [1, 2, 3, 4, 5, i, i * 2, i * 3],
    }


SHARED_DICT = {
    "a": 1, "b": 2, "c": [1, 2, 3, 4, 5],
    "d": {"dd": "deep", "ee": [10, 20, 30]},
    "e": "some string with \"escapes\" and \n newlines",
    "f": True, "g": None, "h": 3.14159,
}

SHARED_LIST = [
    1, 2, 3, "four", 5.0, None, True, False,
    {"a": 1, "b": 2},
    [10, 20, 30, 40],
    "a \"quoted\" thing",
    {"nested": {"deeper": [1, 2, 3]}},
]


# --------------------------- scenario plumbing ------------------------------ #

def run_scenario(name, target_fns, thread_counts=None):
    """Run a scenario in a forked child so a SEGV can't kill the parent."""
    print(f"  Running: {name} ...", end=" ", flush=True)
    sys.stdout.flush()
    sys.stderr.flush()

    pid = os.fork()
    if pid == 0:
        try:
            _run_scenario_threads(target_fns, thread_counts)
            os._exit(0)
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 1
            os._exit(code)
        except BaseException:
            import traceback
            traceback.print_exc()
            os._exit(1)

    deadline = time.monotonic() + SCENARIO_TIMEOUT
    wait_status = None
    while time.monotonic() < deadline:
        r_pid, status = os.waitpid(pid, os.WNOHANG)
        if r_pid != 0:
            wait_status = status
            break
        time.sleep(0.1)

    if wait_status is None:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        os.waitpid(pid, 0)
        print(f"TIMEOUT ({SCENARIO_TIMEOUT}s)")
    elif os.WIFSIGNALED(wait_status):
        sig = os.WTERMSIG(wait_status)
        name_ = (signal.Signals(sig).name
                 if sig in signal.Signals._value2member_map_ else str(sig))
        print(f"CRASH ({name_})")
    elif os.WIFEXITED(wait_status) and os.WEXITSTATUS(wait_status) != 0:
        print(f"FAIL (exit {os.WEXITSTATUS(wait_status)})")
    else:
        print("OK")


def _run_scenario_threads(target_fns, thread_counts=None):
    if thread_counts is None:
        thread_counts = [THREADS] * len(target_fns)

    total = sum(thread_counts)
    barrier = threading.Barrier(total)
    errors = []
    errors_lock = threading.Lock()

    def wrapper(fn):
        def wrapped():
            try:
                barrier.wait()
                fn()
            except Exception as exc:
                with errors_lock:
                    errors.append(repr(exc))
        return wrapped

    threads = []
    for fn, count in zip(target_fns, thread_counts):
        for _ in range(count):
            threads.append(threading.Thread(target=wrapper(fn), daemon=True))

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=SCENARIO_TIMEOUT)

    if errors:
        # Print a few; data races remain the interesting output on stderr.
        for e in errors[:5]:
            print(f"    worker error: {e}", file=sys.stderr)
        sys.exit(1)


# --------------------------- scenarios -------------------------------------- #

def scenario_shared_scanner():
    """N threads share ONE scanner; race on s->memo (SetItem/Clear)."""
    scanner = _make_shared_scanner()
    samples = JSON_SAMPLES

    def worker():
        deadline = time.monotonic() + DURATION
        i = 0
        for _ in range(ITERATIONS):
            doc = samples[i % len(samples)]
            try:
                scanner(doc, 0)
            except Exception:
                pass
            i += 1
            if time.monotonic() > deadline:
                break

    run_scenario("shared scanner (scanner s->memo races)", [worker])


def scenario_shared_encoder_distinct_inputs():
    """N threads share ONE encoder; distinct objects. markers/key_memo races."""
    encoder = _make_shared_encoder()

    def make_worker(tid):
        def worker():
            deadline = time.monotonic() + DURATION
            for i in range(ITERATIONS):
                obj = _make_distinct_object(tid * 1_000_000 + i)
                try:
                    encoder(obj, 0)
                except Exception:
                    pass
                if time.monotonic() > deadline:
                    break
        return worker

    run_scenario(
        "shared encoder, distinct inputs (markers / key_memo races)",
        [make_worker(i) for i in range(THREADS)],
        [1] * THREADS,
    )


def scenario_shared_encoder_shared_dict():
    """All threads encode the SAME dict -> encoder_listencode_dict crit-sect."""
    encoder = _make_shared_encoder()
    shared = SHARED_DICT

    def worker():
        deadline = time.monotonic() + DURATION
        for _ in range(ITERATIONS):
            try:
                encoder(shared, 0)
            except Exception:
                pass
            if time.monotonic() > deadline:
                break

    run_scenario(
        "shared encoder + shared dict (encoder_listencode_dict CS)",
        [worker],
    )


def scenario_shared_encoder_shared_list():
    """All threads encode the SAME list -> encoder_listencode_list crit-sect."""
    encoder = _make_shared_encoder()
    shared = SHARED_LIST

    def worker():
        deadline = time.monotonic() + DURATION
        for _ in range(ITERATIONS):
            try:
                encoder(shared, 0)
            except Exception:
                pass
            if time.monotonic() > deadline:
                break

    run_scenario(
        "shared encoder + shared list (encoder_listencode_list CS)",
        [worker],
    )


def scenario_mutator_vs_readers():
    """Mutator mutates dict while readers encode it. Stresses input CS."""
    encoder = _make_shared_encoder()
    target = {"base": 0, "a": 1, "b": 2, "c": 3, "d": [1, 2, 3]}

    def reader():
        deadline = time.monotonic() + DURATION
        for _ in range(ITERATIONS):
            try:
                encoder(target, 0)
            except Exception:
                pass
            if time.monotonic() > deadline:
                break

    def mutator():
        deadline = time.monotonic() + DURATION
        i = 0
        while i < ITERATIONS * 4 and time.monotonic() < deadline:
            key = f"k{i % 64}"
            try:
                if i & 1:
                    target[key] = [i, i + 1, {"x": i}]
                else:
                    target.pop(key, None)
            except Exception:
                pass
            i += 1

    # One mutator, rest readers.
    reader_count = max(THREADS - 1, 1)
    run_scenario(
        "mutator vs readers on shared dict",
        [reader, mutator],
        [reader_count, 1],
    )


def scenario_module_functions():
    """Concurrent scanstring + encode_basestring_ascii (module-level)."""
    scanstring = _speedups.scanstring
    enc_ascii = _speedups.encode_basestring_ascii

    strings_to_encode = [
        "hello world",
        "\"quoted\" with \\ backslash",
        "\u00e9\u00e8\u00ea \u4e2d\u6587 emoji-\U0001F600",
        "control\n\t\r chars",
        "x" * 256,
    ]
    # For scanstring: the opening quote has been consumed; pass end=1.
    scan_sources = [
        r'"a simple string"',
        r'"with \"escapes\" and \n newlines"',
        r'"unicode \u00e9\u00e8\u4e2d\u6587 stuff"',
        r'"backslashes \\ and slashes \/"',
    ]

    def enc_worker():
        deadline = time.monotonic() + DURATION
        for i in range(ITERATIONS):
            try:
                enc_ascii(strings_to_encode[i % len(strings_to_encode)])
            except Exception:
                pass
            if time.monotonic() > deadline:
                break

    def scan_worker():
        deadline = time.monotonic() + DURATION
        for i in range(ITERATIONS):
            src = scan_sources[i % len(scan_sources)]
            try:
                # scanstring(basestring, end, encoding, strict)
                scanstring(src, 1, "utf-8", 1)
            except Exception:
                pass
            if time.monotonic() > deadline:
                break

    half = max(THREADS // 2, 1)
    run_scenario(
        "module-level scanstring + encode_basestring_ascii",
        [enc_worker, scan_worker],
        [half, max(THREADS - half, 1)],
    )


# --------------------------- main ------------------------------------------- #

SCENARIOS = [
    scenario_shared_scanner,
    scenario_shared_encoder_distinct_inputs,
    scenario_shared_encoder_shared_dict,
    scenario_shared_encoder_shared_list,
    scenario_mutator_vs_readers,
    scenario_module_functions,
]


def main():
    print("TSan stress test for simplejson._speedups")
    print(f"  Python:       {sys.version.splitlines()[0]}")
    print(f"  TSan build:   {_is_tsan_build()}")
    print(f"  PYTHON_GIL:   {os.environ.get('PYTHON_GIL', '<unset>')}")
    print(f"  Threads:      {THREADS}")
    print(f"  Iterations:   {ITERATIONS}")
    print(f"  Duration:     {DURATION}s per scenario")
    print(f"  Timeout:      {SCENARIO_TIMEOUT}s per scenario")
    print()

    for sc in SCENARIOS:
        sc()

    print("\nDone. Inspect stderr (e.g. tsan_report.txt) for TSan warnings.")


if __name__ == "__main__":
    main()
