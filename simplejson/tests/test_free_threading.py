"""Tests that exercise the C extension from multiple threads.

These tests pass on any Python build but their real purpose is to
catch data races on free-threaded builds (PEP 703) where the GIL is
disabled. The test_free_threading CI job runs these with
``PYTHON_GIL=0`` on a free-threaded interpreter.
"""
import sys
import threading
from unittest import TestCase

import simplejson
from simplejson.tests._helpers import skip_if_speedups_missing


class TestFreeThreading(TestCase):
    """Exercise the C extension from multiple threads simultaneously."""

    N_THREADS = 8
    N_ITER = 500

    def _run_threads(self, worker):
        if sys.platform == 'emscripten':
            self.skipTest("threads not available on Emscripten")
        errors = []

        def wrapped():
            try:
                worker()
            except BaseException as e:
                errors.append(e)

        threads = [threading.Thread(target=wrapped)
                   for _ in range(self.N_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        if errors:
            raise errors[0]

    @skip_if_speedups_missing
    def test_concurrent_encode(self):
        data = {
            "numbers": list(range(64)),
            "nested": {"key": "value", "list": [1, 2.5, None, True, False]},
            "string": "hello \u00e9 world",
        }
        expected = simplejson.dumps(data, sort_keys=True)

        def worker():
            for _ in range(self.N_ITER):
                self.assertEqual(
                    simplejson.dumps(data, sort_keys=True), expected)

        self._run_threads(worker)

    @skip_if_speedups_missing
    def test_concurrent_decode(self):
        raw = (
            '{"numbers": [1, 2, 3, 4, 5], '
            '"nested": {"a": "b", "c": [true, false, null]}, '
            '"string": "hello"}'
        )
        expected = simplejson.loads(raw)

        def worker():
            for _ in range(self.N_ITER):
                self.assertEqual(simplejson.loads(raw), expected)

        self._run_threads(worker)

    @skip_if_speedups_missing
    def test_concurrent_encode_decode(self):
        """Mix encode and decode on the same data across threads."""
        data = {"items": list(range(32)), "flag": True, "name": "mix"}
        raw = simplejson.dumps(data, sort_keys=True)

        def worker():
            for _ in range(self.N_ITER):
                s = simplejson.dumps(data, sort_keys=True)
                self.assertEqual(s, raw)
                self.assertEqual(simplejson.loads(s), data)

        self._run_threads(worker)

    @skip_if_speedups_missing
    def test_shared_encoder_instance(self):
        """A single encoder/decoder instance used by many threads."""
        enc = simplejson.JSONEncoder(sort_keys=True)
        dec = simplejson.JSONDecoder()
        data = {"a": 1, "b": [1, 2, 3], "c": {"nested": True}}
        raw = enc.encode(data)

        def worker():
            for _ in range(self.N_ITER):
                self.assertEqual(enc.encode(data), raw)
                self.assertEqual(dec.decode(raw), data)

        self._run_threads(worker)
