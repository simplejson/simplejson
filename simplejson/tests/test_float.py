import math
from unittest import TestCase
from simplejson.compat import long_type, text_type
import simplejson as json
from simplejson.decoder import NaN, PosInf, NegInf
from simplejson.compat import integer_types

class TestFloat(TestCase):
    def test_degenerates_allow(self):
        for inf in (PosInf, NegInf):
            self.assertEqual(json.loads(json.dumps(inf)), inf)
        # Python 2.5 doesn't have math.isnan
        nan = json.loads(json.dumps(NaN))
        self.assertTrue((0 + nan) != nan)

    def test_degenerates_ignore(self):
        for f in (PosInf, NegInf, NaN):
            self.assertEqual(json.loads(json.dumps(f, ignore_nan=True)), None)

    def test_degenerates_deny(self):
        for f in (PosInf, NegInf, NaN):
            self.assertRaises(TypeError, json.dumps, f, allow_nan=False)

    def test_degenerates_with_default(self):
        for f in (PosInf, NegInf, NaN):
            self.assertEqual(
                json.dumps(f, allow_nan=False, default=repr),
                '"%s"' % repr(f))

    def test_degenerates_with_sensible_default(self):
        # shim for ``math.isfinite`` (available only since Python 3.2+)
        def isfinite(o):
            if not isinstance(o, integer_types + (float,)):
                return False
            if o != o or o == PosInf or o == NegInf:
                return False
            return True

        def default(o):
            if isinstance(o, float) and not isfinite(o):
                return {"$float": repr(o)}
            raise TypeError(repr(obj) + " is not JSON serializable")

        floats = (42.1, PosInf, NegInf, NaN)
        self.assertEqual(
            json.dumps(floats, allow_nan=False, default=default),
            '[42.1, {"$float": "inf"}, {"$float": "-inf"}, {"$float": "nan"}]')

    def test_floats(self):
        for num in [1617161771.7650001, math.pi, math.pi**100,
                    math.pi**-100, 3.1]:
            self.assertEqual(float(json.dumps(num)), num)
            self.assertEqual(json.loads(json.dumps(num)), num)
            self.assertEqual(json.loads(text_type(json.dumps(num))), num)

    def test_ints(self):
        for num in [1, long_type(1), 1<<32, 1<<64]:
            self.assertEqual(json.dumps(num), str(num))
            self.assertEqual(int(json.dumps(num)), num)
            self.assertEqual(json.loads(json.dumps(num)), num)
            self.assertEqual(json.loads(text_type(json.dumps(num))), num)
