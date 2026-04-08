"""Tests for free-threaded Python (PEP 703) thread safety.

These tests exercise concurrent encoding and decoding to detect data races
and deadlocks in the C extension. They are useful on all Python versions
but most meaningful on free-threaded builds (3.13t+) where the GIL does
not serialize access.
"""
from __future__ import absolute_import
import sys
import threading
import unittest
from unittest import TestCase

import simplejson as json


# Number of threads and iterations to use for concurrency tests.
# Keep these moderate to avoid making the test suite too slow while
# still providing meaningful coverage for race conditions.
NUM_THREADS = 8
NUM_ITERATIONS = 100


def _has_speedups():
    from simplejson import encoder
    return encoder.c_make_encoder is not None


def skip_if_no_speedups(func):
    def wrapper(*args, **kwargs):
        if not _has_speedups():
            if hasattr(unittest, 'SkipTest'):
                raise unittest.SkipTest("C Extension not available")
            return
        return func(*args, **kwargs)
    return wrapper


class TestFreeThreadingEncode(TestCase):
    """Test concurrent encoding operations for thread safety."""

    def _run_concurrent(self, func, num_threads=NUM_THREADS):
        """Run func concurrently in multiple threads, collect errors."""
        errors = []
        barrier = threading.Barrier(num_threads)

        def worker():
            try:
                barrier.wait()
                func()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        if errors:
            raise errors[0]

    def test_concurrent_dumps_simple(self):
        """Concurrent dumps of simple types should not race."""
        def work():
            for _ in range(NUM_ITERATIONS):
                assert json.dumps(None) == 'null'
                assert json.dumps(True) == 'true'
                assert json.dumps(False) == 'false'
                assert json.dumps(42) == '42'
                assert json.dumps(3.14) == '3.14'
                assert json.dumps("hello") == '"hello"'

        self._run_concurrent(work)

    def test_concurrent_dumps_dict(self):
        """Concurrent dumps of dicts should not race."""
        data = {"key": "value", "number": 42, "nested": {"a": 1, "b": 2}}

        def work():
            for _ in range(NUM_ITERATIONS):
                result = json.dumps(data, sort_keys=True)
                expected = '{"key": "value", "nested": {"a": 1, "b": 2}, "number": 42}'
                assert result == expected, "%r != %r" % (result, expected)

        self._run_concurrent(work)

    def test_concurrent_dumps_list(self):
        """Concurrent dumps of lists should not race."""
        data = [1, "two", 3.0, None, True, [4, 5, 6]]

        def work():
            for _ in range(NUM_ITERATIONS):
                result = json.dumps(data)
                assert result == '[1, "two", 3.0, null, true, [4, 5, 6]]'

        self._run_concurrent(work)

    def test_concurrent_dumps_sort_keys(self):
        """Concurrent encoding with sort_keys should not race."""
        data = {"z": 1, "a": 2, "m": 3, "b": 4}

        def work():
            for _ in range(NUM_ITERATIONS):
                result = json.dumps(data, sort_keys=True)
                assert result == '{"a": 2, "b": 4, "m": 3, "z": 1}'

        self._run_concurrent(work)

    def test_concurrent_dumps_varied_types(self):
        """Concurrent encoding of different types should not race."""
        import decimal

        datasets = [
            {"type": "dict", "data": {"key": "value"}},
            {"type": "list", "data": [1, 2, 3]},
            {"type": "string", "data": "hello world"},
            {"type": "unicode", "data": u"\u00e9\u00e8\u00ea"},
            {"type": "number", "data": 12345},
            {"type": "float", "data": 1.23456},
            {"type": "null", "data": None},
            {"type": "bool", "data": True},
        ]

        def work():
            for _ in range(NUM_ITERATIONS):
                for item in datasets:
                    json.dumps(item)

        self._run_concurrent(work)

    @skip_if_no_speedups
    def test_concurrent_encode_basestring_ascii(self):
        """Concurrent calls to the C encode_basestring_ascii should not race."""
        from simplejson import _speedups

        strings = [
            "simple",
            "with\nnewline",
            "with\ttab",
            u"\u00e9\u00e8\u00ea",
            u"\U0001f600",
            "with \"quotes\"",
            "with \\backslash",
        ]

        def work():
            for _ in range(NUM_ITERATIONS):
                for s in strings:
                    _speedups.encode_basestring_ascii(s)

        self._run_concurrent(work)

    @skip_if_no_speedups
    def test_concurrent_scanstring(self):
        """Concurrent calls to the C scanstring should not race."""
        from simplejson import _speedups

        json_strings = [
            '"simple"',
            '"with\\nnewline"',
            '"with\\ttab"',
            '"with\\u00e9unicode"',
            '"with\\\\"backslash"',
        ]

        def work():
            for _ in range(NUM_ITERATIONS):
                for s in json_strings:
                    _speedups.scanstring(s, 1, True)

        self._run_concurrent(work)


class TestFreeThreadingDecode(TestCase):
    """Test concurrent decoding operations for thread safety."""

    def _run_concurrent(self, func, num_threads=NUM_THREADS):
        """Run func concurrently in multiple threads, collect errors."""
        errors = []
        barrier = threading.Barrier(num_threads)

        def worker():
            try:
                barrier.wait()
                func()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        if errors:
            raise errors[0]

    def test_concurrent_loads_simple(self):
        """Concurrent loads of simple JSON should not race."""
        def work():
            for _ in range(NUM_ITERATIONS):
                assert json.loads('null') is None
                assert json.loads('true') is True
                assert json.loads('false') is False
                assert json.loads('42') == 42
                assert json.loads('3.14') == 3.14
                assert json.loads('"hello"') == "hello"

        self._run_concurrent(work)

    def test_concurrent_loads_dict(self):
        """Concurrent loads of JSON objects should not race."""
        json_str = '{"key": "value", "number": 42, "nested": {"a": 1}}'

        def work():
            for _ in range(NUM_ITERATIONS):
                result = json.loads(json_str)
                assert result == {"key": "value", "number": 42, "nested": {"a": 1}}

        self._run_concurrent(work)

    def test_concurrent_loads_list(self):
        """Concurrent loads of JSON arrays should not race."""
        json_str = '[1, "two", 3.0, null, true, [4, 5, 6]]'

        def work():
            for _ in range(NUM_ITERATIONS):
                result = json.loads(json_str)
                assert result == [1, "two", 3.0, None, True, [4, 5, 6]]

        self._run_concurrent(work)

    def test_concurrent_loads_with_parse_float(self):
        """Concurrent loads with custom parse_float should not race."""
        import decimal

        json_str = '{"price": 19.99, "tax": 1.50}'

        def work():
            for _ in range(NUM_ITERATIONS):
                result = json.loads(json_str, parse_float=decimal.Decimal)
                assert result["price"] == decimal.Decimal("19.99")
                assert result["tax"] == decimal.Decimal("1.50")

        self._run_concurrent(work)

    def test_concurrent_loads_large(self):
        """Concurrent loads of larger JSON should not race."""
        data = {
            "users": [
                {"id": i, "name": "user_%d" % i, "active": i % 2 == 0}
                for i in range(50)
            ]
        }
        json_str = json.dumps(data)

        def work():
            for _ in range(NUM_ITERATIONS):
                result = json.loads(json_str)
                assert len(result["users"]) == 50

        self._run_concurrent(work)


class TestFreeThreadingMixed(TestCase):
    """Test concurrent mixed encode/decode operations."""

    def _run_concurrent(self, func, num_threads=NUM_THREADS):
        """Run func concurrently in multiple threads, collect errors."""
        errors = []
        barrier = threading.Barrier(num_threads)

        def worker():
            try:
                barrier.wait()
                func()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        if errors:
            raise errors[0]

    def test_concurrent_roundtrip(self):
        """Concurrent encode+decode roundtrips should not race."""
        data = {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "null": None,
            "bool": True,
            "list": [1, 2, 3],
            "nested": {"a": {"b": {"c": 1}}},
        }

        def work():
            for _ in range(NUM_ITERATIONS):
                encoded = json.dumps(data, sort_keys=True)
                decoded = json.loads(encoded)
                re_encoded = json.dumps(decoded, sort_keys=True)
                assert encoded == re_encoded

        self._run_concurrent(work)

    def test_concurrent_encode_decode_different_data(self):
        """Threads encoding and decoding different data simultaneously."""
        errors = []
        barrier = threading.Barrier(NUM_THREADS)

        def encoder_work():
            try:
                barrier.wait()
                for i in range(NUM_ITERATIONS):
                    data = {"thread": "encoder", "iter": i, "values": list(range(10))}
                    result = json.dumps(data)
                    assert '"thread": "encoder"' in result
            except Exception as e:
                errors.append(e)

        def decoder_work():
            try:
                barrier.wait()
                for i in range(NUM_ITERATIONS):
                    json_str = '{"thread": "decoder", "iter": %d, "values": [0,1,2]}' % i
                    result = json.loads(json_str)
                    assert result["thread"] == "decoder"
                    assert result["iter"] == i
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(NUM_THREADS):
            if i % 2 == 0:
                threads.append(threading.Thread(target=encoder_work))
            else:
                threads.append(threading.Thread(target=decoder_work))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        if errors:
            raise errors[0]

    @skip_if_no_speedups
    def test_concurrent_encoder_creation(self):
        """Concurrent creation of C encoder objects should not race."""
        def work():
            for _ in range(NUM_ITERATIONS):
                enc = json.JSONEncoder(sort_keys=True)
                result = enc.encode({"a": 1, "b": 2})
                assert result == '{"a": 1, "b": 2}'

        errors = []
        barrier = threading.Barrier(NUM_THREADS)

        def worker():
            try:
                barrier.wait()
                work()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(NUM_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        if errors:
            raise errors[0]

    @skip_if_no_speedups
    def test_concurrent_decoder_creation(self):
        """Concurrent creation of C decoder/scanner objects should not race."""
        def work():
            for _ in range(NUM_ITERATIONS):
                dec = json.JSONDecoder()
                result = dec.decode('{"a": 1, "b": 2}')
                assert result == {"a": 1, "b": 2}

        errors = []
        barrier = threading.Barrier(NUM_THREADS)

        def worker():
            try:
                barrier.wait()
                work()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(NUM_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        if errors:
            raise errors[0]
