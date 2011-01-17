from decimal import Decimal
from unittest import TestCase
from StringIO import StringIO

import simplejson as json

class TestDecimal(TestCase):
    NUMS = "1.0", "10.00", "1.1", "1234567890.1234567890", "500"
    def dumps(self, obj, **kw):
        sio = StringIO()
        json.dump(obj, sio, **kw)
        res = json.dumps(obj, **kw)
        self.assertEquals(res, sio.getvalue())
        return res

    def loads(self, s, **kw):
        sio = StringIO(s)
        res = json.loads(s, **kw)
        self.assertEquals(res, json.load(sio, **kw))
        return res

    def test_decimal_encode(self):
        for d in map(Decimal, self.NUMS):
            self.assertEquals(self.dumps(d, use_decimal=True), str(d))
    
    def test_decimal_decode(self):
        for s in self.NUMS:
            self.assertEquals(self.loads(s, parse_float=Decimal), Decimal(s))
    
    def test_decimal_roundtrip(self):
        for d in map(Decimal, self.NUMS):
            # The type might not be the same (int and Decimal) but they
            # should still compare equal.
            self.assertEquals(
                self.loads(
                    self.dumps(d, use_decimal=True), parse_float=Decimal),
                d)
            self.assertEquals(
                self.loads(
                    self.dumps([d], use_decimal=True), parse_float=Decimal),
                [d])

    def test_decimal_defaults(self):
        d = Decimal(1)
        sio = StringIO()
        # use_decimal=False is the default
        self.assertRaises(TypeError, json.dumps, d, use_decimal=False)
        self.assertRaises(TypeError, json.dumps, d)
        self.assertRaises(TypeError, json.dump, d, sio, use_decimal=False)
        self.assertRaises(TypeError, json.dump, d, sio)