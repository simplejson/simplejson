# AGENTS.md

Notes for Claude and other agents working on simplejson. This is
tribal knowledge that isn't obvious from reading the source — the
code structure itself is straightforward enough; what's collected
here is the workflow, debugging tricks, and pitfalls specifically
learned during the 3.14t / free-threading port.

## Testing against alternate Python versions locally

Use `uv` + `python-build-standalone`, **not** `apt install python3.X-dbg`
and **not** building CPython from source. uv pulls prebuilt CPython
variants (including debug and free-threaded debug) in under 10 seconds:

```bash
# Regular release (same thing setup-python installs in CI)
uv python install cpython-3.14.4

# Debug build — exposes sys.gettotalrefcount, Py_DECREF asserts,
# and the internal consistency checks release builds skip. This is
# the variant that caught the -1LL << n UB bug.
uv python install cpython-3.14.4+debug

# Free-threaded + debug — highest-value single variant for this PR.
# Stacks refcount asserts, GIL-disabled scheduling, and the
# specializer in one interpreter.
uv python install cpython-3.14.4+freethreaded+debug
```

Each installed Python is a self-contained directory under
`~/.local/share/uv/python/`. Make a venv and install `setuptools`+
`wheel` with `uv pip`:

```bash
uv venv --python cpython-3.14.4+debug /tmp/debug-venv
uv pip install --python /tmp/debug-venv/bin/python setuptools wheel
rm -f simplejson/_speedups*.so
REQUIRE_SPEEDUPS=1 /tmp/debug-venv/bin/python setup.py build_ext -i
/tmp/debug-venv/bin/python -m simplejson.tests._cibw_runner .
```

**Always use `_cibw_runner`, not `python -m unittest discover`.** The
runner runs the full test suite twice: once with the C speedups
loaded, once via `NoExtensionTestSuite` with `simplejson._toggle_speedups(False)`
to exercise the pure-Python path. `unittest discover` only hits
the C path.

## What uv can't give you: Python 2.7

python-build-standalone does not ship Py2.7 binaries. There is **no
way to test Py2 locally**. When touching code that affects the Py2
bytes parser path in `_speedups.c` or `_speedups_scan.h`, the loop is:

1. Reason about the change on paper (macro expansions, declarations
   vs statements, refcount transitions)
2. Push a commit
3. Wait for the `Build Python 2.7 wheels` step in the wheel job
   (uses `pypa/cibuildwheel@v1.12.0` / manylinux1 / gcc 4.8)

## Reading CI failures

The GitHub Actions raw logs endpoint requires **admin** permissions —
the API returns 403 for anyone else, and `WebFetch` against a job
page only sees the failure *annotations*, not the actual step output.

When you see an annotation like `pip wheel ... failed with code 1`
and no detail:

1. Reproduce locally across `python3.10`..`python3.14.4` and both
   free-threaded + debug via uv. 90% of real failures reproduce.
2. Check if the run is **stale** — compare the run's head SHA
   against the branch head. `mcp__github__list_commits` for the
   branch, and compare with run URLs or `mcp__github__list_pull_requests`.
   CI runs frequently lag by seconds, and multiple pushes within
   ~30 seconds will leave stale failure notifications in the
   webhook stream.
3. If the local reproduction is clean, ask the user to paste the
   raw log lines. This is almost always faster than guessing.

## cibuildwheel gotchas on this repo

Two cibuildwheel versions run in one job:

- **Main `Build wheels` step** uses `pypa/cibuildwheel@v3.4.1` (Py3).
  In v3.x **PyPy is disabled by default**; `CIBW_SKIP: "pp*"` *errors*
  with `Invalid skip selector: 'pp*'. This selector matches a group
  that wasn't enabled.` Do not set it.
- **`Build Python 2.7 wheels` step** uses `pypa/cibuildwheel@v1.12.0`.
  That version *does* build PyPy by default, so this step **must**
  keep `CIBW_SKIP: "pp*"`.
- `CIBW_ENABLE: "cpython-freethreading"` is deprecated in v3.4+
  (free-threaded builds are on by default). Remove it.

## Extension module reload does not actually reload

`importlib.reload(simplejson._speedups)` and
`del sys.modules['simplejson._speedups']; import simplejson._speedups`
both return the **same cached module object** from CPython's import
cache — `module_exec` is not re-run. The only scenario that actually
triggers a fresh `module_exec` against the pre-3.13 static state is
a **subinterpreter import on Python 3.5–3.11**. That's why
`reset_speedups_state_constants` exists as defense-in-depth, but
it's nearly impossible to exercise from a unit test. Don't waste
time writing one.

## Refcount leak tests flake on 3.14 debug

CPython 3.14 debug has non-trivial per-call refcount drift from
specializer inline caches settling in — up to ~272 refs over 2000
iterations of `simplejson.dumps(...)` with no real leak.
`TestRefcountLeaks` in `test_speedups.py` uses a **two-phase**
measurement: warmup + first 2000 iters absorb the noise, second
2000 iters should show <10 refs. **Assert on phase 2 only.**
Asserting on the total delta will flake.

## Python 3.14 release has `-Wunreachable-code` in its default CFLAGS

Earlier Python versions don't. A local release build with `-Werror`
will pass on 3.11/3.12/3.13 and fail on 3.14 if you introduce any
unreachable code on a hot path. Always spot-check with
`cpython-3.14.4` specifically when doing C refactors.

## `_speedups_scan.h` is included **twice**

From `_speedups.c`, once with `JSON_SCAN_SUFFIX=_unicode` (used by
every Python 3 and by Py2 unicode input) and once on Py2 with
`JSON_SCAN_SUFFIX=_str`. The macros are `#undef`-ed at the bottom
of the file so the second include can redefine them. GCC's
multi-include-guard optimization does not kick in because the only
`#ifndef` in the file is a sanity check on `JSON_SCAN_SUFFIX`, not
a wrap-the-whole-file include guard.

`scan_once`, `_parse_object`, `_parse_array`, and `_match_number`
live in the template. `scanstring_str` and `scanstring_unicode` do
**not** — they remain separate because `scanstring_str` has a Py2
hybrid return type (bytes when ASCII-only, unicode otherwise) that
the template can't cleanly express. Don't try to pull them in.

## Don't `Py_CLEAR` type fields in `reset_speedups_state_constants`

On pre-3.13, `state->PyScannerType` and `state->PyEncoderType` hold
**borrowed** pointers to static `PyTypeObject` bodies defined later
in the file. They must never be refcounted. The reset helper is for
*constants* only; `speedups_clear` on 3.13+ handles type fields
separately.

## `REQUIRE_SPEEDUPS=1` only affects the build, not tests

It makes `setup.py build_ext` fail loudly instead of falling back to
pure-Python. It is a **no-op** on `python -m unittest` or
`_cibw_runner` invocations. If the built `.so` is subtly broken
(e.g. imports but `simplejson.encoder.c_make_encoder is None`), the
test runner's `TestMissingSpeedups` calls `skipTest()` not `fail()`
and the whole C-extension suite silently passes as "all skipped".

Both `test_free_threading` and `test_debug_build` CI jobs include
an explicit wiring check:

```python
import simplejson, simplejson.encoder, simplejson.scanner
from simplejson._speedups import make_encoder, make_scanner
assert simplejson.encoder.c_make_encoder is make_encoder
assert simplejson.scanner.c_make_scanner is make_scanner
```

**Keep this check.** It's the only thing that catches a silently-
broken wheel.

## GitHub Actions version pinning landmines

- `astral-sh/setup-uv` floating `@v8` tag didn't exist when this PR
  was written — only the pinned `@v8.0.0`. Web searches may
  confidently tell you `v8` exists when it doesn't. Verify via
  `git ls-remote --tags`.
- `actions/setup-python@v5` floats and works fine; no version
  landmine there.
- Pinning `@v5.6.0.6.0` (mangled) is an easy typo that silently
  doesn't resolve. Double-check the exact tag string before trusting.

## Test helpers live in `simplejson/tests/_helpers.py`

`has_speedups()` and `skip_if_speedups_missing()` are **not** defined
in each test file. Import them:

```python
from simplejson.tests._helpers import skip_if_speedups_missing
```

## Useful CFLAGS combinations

```bash
# Everything on, matches the test_debug_build CI job. Use this for
# the standard (non-free-threaded) debug and release builds.
CFLAGS="-Wall -Wextra -Wshadow -Wstrict-prototypes -Werror \
        -Wno-unused-parameter -Wno-missing-field-initializers \
        -Wno-cast-function-type"

# Add -Wdeclaration-after-statement to verify the file stays C89-clean.
# Works on standard and standard-debug builds but NOT on free-threaded
# builds: cp314t's own `refcount.h` has a mixed-decls-and-code block
# (around refcount.h:113) that trips -Werror before your source is
# even compiled. Use the plain CFLAGS above when building against
# cpython-3.14+freethreaded+debug.
CFLAGS="-Wall -Wextra -Wshadow -Wstrict-prototypes -Wdeclaration-after-statement \
        -Werror -Wno-unused-parameter -Wno-missing-field-initializers \
        -Wno-cast-function-type"
```

`-Wno-unused-parameter` and `-Wno-missing-field-initializers` are
necessary because Python's own headers trigger them — removing them
causes a build failure that's not your fault. Keep them suppressed.
