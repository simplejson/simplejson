import sys
import math
from unittest import TestCase
from simplejson.compat import long_type, text_type
import simplejson as json
from simplejson.decoder import NaN, PosInf, NegInf

class TestFloat(TestCase):
    def test_degenerates_allow(self):
        for inf in (PosInf, NegInf):
            self.assertEqual(json.loads(json.dumps(inf, allow_nan=True), allow_nan=True), inf)
        # Python 2.5 doesn't have math.isnan
        nan = json.loads(json.dumps(NaN, allow_nan=True), allow_nan=True)
        self.assertTrue((0 + nan) != nan)

    def test_degenerates_ignore(self):
        for f in (PosInf, NegInf, NaN):
            self.assertEqual(json.loads(json.dumps(f, ignore_nan=True)), None)

    def test_degenerates_deny(self):
        for f in (PosInf, NegInf, NaN):
            self.assertRaises(ValueError, json.dumps, f, allow_nan=False)
        for s in ('Infinity', '-Infinity', 'NaN'):
            self.assertRaises(ValueError, json.loads, s, allow_nan=False)
            self.assertRaises(ValueError, json.loads, s)

    def test_degenerates_deny_message(self):
        # The error names the value, as the pure Python encoder does.
        for f, text in ((PosInf, 'inf'), (NegInf, '-inf'), (NaN, 'nan')):
            try:
                json.dumps(f, allow_nan=False)
            except ValueError:
                e = sys.exc_info()[1]
                self.assertEqual(
                    str(e),
                    'Out of range float values are not JSON compliant: ' + text)
            else:
                self.fail('Unexpected success encoding %r' % (f,))

    def test_degenerates_deny_message_float_subclass(self):
        # The error names the value with repr(), as the pure Python encoder
        # does, so a float subclass is named by its own __repr__ on both the
        # C and the pure Python path.
        class CustomReprFloat(float):
            def __repr__(self):
                return 'CustomReprFloat(%s)' % float.__repr__(self)

        for text in ('inf', '-inf', 'nan'):
            f = CustomReprFloat(text)
            for value in (f, [f], {'k': f}, {f: 1}):
                try:
                    json.dumps(value, allow_nan=False)
                except ValueError:
                    e = sys.exc_info()[1]
                    self.assertEqual(
                        str(e),
                        'Out of range float values are not JSON compliant: '
                        'CustomReprFloat(%s)' % text)
                else:
                    self.fail('Unexpected success encoding %r' % (value,))

    def test_degenerates_deny_repr_error_propagates(self):
        # An exception raised by __repr__ while naming the value propagates
        # unchanged instead of being replaced by the ValueError.
        class ReprError(Exception):
            pass

        class RaisingReprFloat(float):
            def __repr__(self):
                raise ReprError('repr failed')

        f = RaisingReprFloat('inf')
        for value in (f, [f], {f: 1}):
            self.assertRaises(ReprError, json.dumps, value, allow_nan=False)

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

    def test_float_range(self):
        try:
            float_range = [sys.float_info.min, sys.float_info.max]
        except AttributeError:
            float_range = [2.2250738585072014e-308, 1.7976931348623157e+308]
        self.assertEqual(json.loads(json.dumps(float_range)), float_range)
