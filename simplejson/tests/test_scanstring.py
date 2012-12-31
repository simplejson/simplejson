import sys
from unittest import TestCase

import simplejson as json
import simplejson.decoder
from simplejson.compat import b, PY3

class TestScanString(TestCase):
    # The bytes type is intentionally not used in most of these tests
    # under Python 3 because the decoder immediately coerces to str before
    # calling scanstring. In Python 2 we are testing the code paths
    # for both unicode and str.
    #
    # The reason this is done is because Python 3 would require
    # entirely different code paths for parsing bytes and str.
    #
    def test_py_scanstring(self):
        self._test_scanstring(simplejson.decoder.py_scanstring)

    def test_c_scanstring(self):
        if not simplejson.decoder.c_scanstring:
            return
        self._test_scanstring(simplejson.decoder.c_scanstring)

    def _test_scanstring(self, scanstring):
        self.assertEquals(
            scanstring('"z\\ud834\\udd20x"', 1, None, True),
            (u'z\U0001d120x', 16))

        if sys.maxunicode == 65535:
            self.assertEquals(
                scanstring(u'"z\U0001d120x"', 1, None, True),
                (u'z\U0001d120x', 6))
        else:
            self.assertEquals(
                scanstring(u'"z\U0001d120x"', 1, None, True),
                (u'z\U0001d120x', 5))

        self.assertEquals(
            scanstring('"\\u007b"', 1, None, True),
            (u'{', 8))

        self.assertEquals(
            scanstring('"A JSON payload should be an object or array, not a string."', 1, None, True),
            (u'A JSON payload should be an object or array, not a string.', 60))

        self.assertEquals(
            scanstring('["Unclosed array"', 2, None, True),
            (u'Unclosed array', 17))

        self.assertEquals(
            scanstring('["extra comma",]', 2, None, True),
            (u'extra comma', 14))

        self.assertEquals(
            scanstring('["double extra comma",,]', 2, None, True),
            (u'double extra comma', 21))

        self.assertEquals(
            scanstring('["Comma after the close"],', 2, None, True),
            (u'Comma after the close', 24))

        self.assertEquals(
            scanstring('["Extra close"]]', 2, None, True),
            (u'Extra close', 14))

        self.assertEquals(
            scanstring('{"Extra comma": true,}', 2, None, True),
            (u'Extra comma', 14))

        self.assertEquals(
            scanstring('{"Extra value after close": true} "misplaced quoted value"', 2, None, True),
            (u'Extra value after close', 26))

        self.assertEquals(
            scanstring('{"Illegal expression": 1 + 2}', 2, None, True),
            (u'Illegal expression', 21))

        self.assertEquals(
            scanstring('{"Illegal invocation": alert()}', 2, None, True),
            (u'Illegal invocation', 21))

        self.assertEquals(
            scanstring('{"Numbers cannot have leading zeroes": 013}', 2, None, True),
            (u'Numbers cannot have leading zeroes', 37))

        self.assertEquals(
            scanstring('{"Numbers cannot be hex": 0x14}', 2, None, True),
            (u'Numbers cannot be hex', 24))

        self.assertEquals(
            scanstring('[[[[[[[[[[[[[[[[[[[["Too deep"]]]]]]]]]]]]]]]]]]]]', 21, None, True),
            (u'Too deep', 30))

        self.assertEquals(
            scanstring('{"Missing colon" null}', 2, None, True),
            (u'Missing colon', 16))

        self.assertEquals(
            scanstring('{"Double colon":: null}', 2, None, True),
            (u'Double colon', 15))

        self.assertEquals(
            scanstring('{"Comma instead of colon", null}', 2, None, True),
            (u'Comma instead of colon', 25))

        self.assertEquals(
            scanstring('["Colon instead of comma": false]', 2, None, True),
            (u'Colon instead of comma', 25))

        self.assertEquals(
            scanstring('["Bad value", truth]', 2, None, True),
            (u'Bad value', 12))

        for c in map(chr, range(0x00, 0x1f)):
            self.assertEquals(
                scanstring(c + '"', 0, None, False),
                (c, 2))
            self.assertRaises(
                ValueError,
                scanstring, c + '"', 0, None, True)

        self.assertRaises(ValueError, scanstring, '', 0, None, True)
        self.assertRaises(ValueError, scanstring, 'a', 0, None, True)
        self.assertRaises(ValueError, scanstring, '\\', 0, None, True)
        self.assertRaises(ValueError, scanstring, '\\u', 0, None, True)
        self.assertRaises(ValueError, scanstring, '\\u0', 0, None, True)
        self.assertRaises(ValueError, scanstring, '\\u01', 0, None, True)
        self.assertRaises(ValueError, scanstring, '\\u012', 0, None, True)
        self.assertRaises(ValueError, scanstring, '\\u0123', 0, None, True)
        if sys.maxunicode > 65535:
            self.assertRaises(ValueError, scanstring, '\\ud834"', 0, None, True),
            self.assertRaises(ValueError, scanstring, '\\ud834\\u"', 0, None, True),
            self.assertRaises(ValueError, scanstring, '\\ud834\\x0123"', 0, None, True),

    def test_issue3623(self):
        self.assertRaises(ValueError, json.decoder.scanstring, "xxx", 1,
                          "xxx")
        self.assertRaises(UnicodeDecodeError,
                          json.encoder.encode_basestring_ascii, b("xx\xff"))

    def test_overflow(self):
        # Python 2.5 does not have maxsize, Python 3 does not have maxint
        maxsize = getattr(sys, 'maxsize', getattr(sys, 'maxint', None))
        assert maxsize is not None
        self.assertRaises(OverflowError, json.decoder.scanstring, "xxx",
                          maxsize + 1)
