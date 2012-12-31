import math
from unittest import TestCase
from simplejson.compat import long_type, text_type
import simplejson as json
from simplejson.decoder import NaN, PosInf, NegInf

class TestFloat(TestCase):
    def test_degenerates(self):
        for inf in (PosInf, NegInf):
            self.assertEquals(json.loads(json.dumps(inf)), inf)
        # Python 2.5 doesn't have math.isnan
        nan = json.loads(json.dumps(NaN))
        self.assert_((0 + nan) != nan)

    def test_floats(self):
        for num in [1617161771.7650001, math.pi, math.pi**100,
                    math.pi**-100, 3.1]:
            self.assertEquals(float(json.dumps(num)), num)
            self.assertEquals(json.loads(json.dumps(num)), num)
            self.assertEquals(json.loads(text_type(json.dumps(num))), num)

    def test_ints(self):
        for num in [1, long_type(1), 1<<32, 1<<64]:
            self.assertEquals(json.dumps(num), str(num))
            self.assertEquals(int(json.dumps(num)), num)
            self.assertEquals(json.loads(json.dumps(num)), num)
            self.assertEquals(json.loads(text_type(json.dumps(num))), num)
