import sys
import unittest
from unittest import TestCase

import simplejson
from simplejson import encoder, decoder, scanner
from simplejson.compat import PY3


def has_speedups():
    return encoder.c_make_encoder is not None


def skip_if_speedups_missing(func):
    def wrapper(*args, **kwargs):
        if not has_speedups():
            if hasattr(unittest, 'SkipTest'):
                raise unittest.SkipTest("C Extension not available")
            else:
                sys.stdout.write("C Extension not available")
                return
        return func(*args, **kwargs)

    return wrapper


class BadBool:
    def __bool__(self):
        1/0
    __nonzero__ = __bool__


class TestDecode(TestCase):
    @skip_if_speedups_missing
    def test_make_scanner(self):
        self.assertRaises(AttributeError, scanner.c_make_scanner, 1)

    @skip_if_speedups_missing
    def test_bad_bool_args(self):
        with self.assertRaises(ZeroDivisionError):
            decoder.JSONDecoder(strict=BadBool()).decode('""')
        with self.assertRaises(ZeroDivisionError):
            decoder.JSONDecoder(strict=BadBool()).decode('{}')
        if not PY3:
            with self.assertRaises(ZeroDivisionError):
                decoder.JSONDecoder(strict=BadBool()).decode(u'""')
            with self.assertRaises(ZeroDivisionError):
                decoder.JSONDecoder(strict=BadBool()).decode(u'{}')

class TestEncode(TestCase):
    @skip_if_speedups_missing
    def test_make_encoder(self):
        self.assertRaises(
            TypeError,
            encoder.c_make_encoder,
            None,
            ("\xCD\x7D\x3D\x4E\x12\x4C\xF9\x79\xD7"
             "\x52\xBA\x82\xF2\x27\x4A\x7D\xA0\xCA\x75"),
            None
        )

    @skip_if_speedups_missing
    def test_bad_bool_args(self):
        with self.assertRaises(ZeroDivisionError):
            encoder.JSONEncoder(skipkeys=BadBool()).encode({})
        with self.assertRaises(ZeroDivisionError):
            encoder.JSONEncoder(ensure_ascii=BadBool()).encode({})
        with self.assertRaises(ZeroDivisionError):
            encoder.JSONEncoder(check_circular=BadBool()).encode({})
        with self.assertRaises(ZeroDivisionError):
            encoder.JSONEncoder(allow_nan=BadBool()).encode({})
        with self.assertRaises(ZeroDivisionError):
            encoder.JSONEncoder(sort_keys=BadBool()).encode({})
        with self.assertRaises(ZeroDivisionError):
            encoder.JSONEncoder(use_decimal=BadBool()).encode({})
        with self.assertRaises(ZeroDivisionError):
            encoder.JSONEncoder(namedtuple_as_object=BadBool()).encode({})
        with self.assertRaises(ZeroDivisionError):
            encoder.JSONEncoder(tuple_as_array=BadBool()).encode({})
        with self.assertRaises(ZeroDivisionError):
            encoder.JSONEncoder(bigint_as_string=BadBool()).encode({})
        with self.assertRaises(ZeroDivisionError):
            encoder.JSONEncoder(for_json=BadBool()).encode({})
        with self.assertRaises(ZeroDivisionError):
            encoder.JSONEncoder(ignore_nan=BadBool()).encode({})
        with self.assertRaises(ZeroDivisionError):
            encoder.JSONEncoder(iterable_as_array=BadBool()).encode({})

    @skip_if_speedups_missing
    def test_int_as_string_bitcount_overflow(self):
        with self.assertRaises((TypeError, OverflowError)):
            encoder.JSONEncoder(int_as_string_bitcount=2**32+31).encode(0)
