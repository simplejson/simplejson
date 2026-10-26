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


class AlwaysEqualFloat(float):
    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    __hash__ = float.__hash__


class AlwaysUnequalFloat(float):
    def __eq__(self, other):
        return False

    def __ne__(self, other):
        return True

    __hash__ = float.__hash__


class RaisingComparisonFloat(float):
    def __eq__(self, other):
        raise AssertionError('float comparison hook called')

    def __ne__(self, other):
        raise AssertionError('float comparison hook called')

    __hash__ = float.__hash__


class TestFloatSubclassComparison(TestCase):
    subclasses = (AlwaysEqualFloat, AlwaysUnequalFloat, RaisingComparisonFloat)
    wrappers = (lambda value: value, lambda value: [value],
                lambda value: {'value': value}, lambda value: {value: 'value'})

    def test_finite_classification(self):
        for subclass in self.subclasses:
            for value in (0.0, -0.0, 1.5, -1.5, sys.float_info.max):
                for wrap in self.wrappers:
                    for use_decimal in (False, True):
                        for indent in (None, 2):
                            for options in ({}, {'allow_nan': True},
                                            {'ignore_nan': True}):
                                options = dict(options, use_decimal=use_decimal,
                                               indent=indent)
                                self.assertEqual(
                                    json.dumps(wrap(subclass(value)), **options),
                                    json.dumps(wrap(value), **options))

    def test_nonfinite_allowed_or_ignored(self):
        for subclass in self.subclasses:
            for value in (NaN, PosInf, NegInf):
                for wrap in self.wrappers:
                    for use_decimal in (False, True):
                        for indent in (None, 2):
                            for options in ({'allow_nan': True},
                                            {'ignore_nan': True},
                                            {'allow_nan': True, 'ignore_nan': True}):
                                options = dict(options, use_decimal=use_decimal,
                                               indent=indent)
                                self.assertEqual(
                                    json.dumps(wrap(subclass(value)), **options),
                                    json.dumps(wrap(value), **options))

    def test_nonfinite_denied(self):
        for subclass in self.subclasses:
            for value in (NaN, PosInf, NegInf):
                for wrap in self.wrappers:
                    for use_decimal in (False, True):
                        self.assertRaises(
                            ValueError, json.dumps, wrap(subclass(value)),
                            allow_nan=False, use_decimal=use_decimal)

    def test_finite_conversion_hook_is_preserved(self):
        class ConvertedFloat(float):
            calls = 0

            def __float__(self):
                self.calls += 1
                return 42.0

        class RaisingConversionFloat(float):
            def __float__(self):
                raise RuntimeError('float conversion hook called')

        for wrap in self.wrappers:
            value = ConvertedFloat(1.5)
            self.assertEqual(json.dumps(wrap(value)), json.dumps(wrap(42.0)))
            self.assertEqual(value.calls, 1)
            self.assertRaises(RuntimeError, json.dumps,
                              wrap(RaisingConversionFloat(1.5)))

    def test_nonfinite_does_not_call_conversion_hook(self):
        class NonfiniteFloat(RaisingComparisonFloat):
            def __float__(self):
                raise AssertionError('nonfinite conversion hook called')

        for value in (NaN, PosInf, NegInf):
            for options in ({'allow_nan': True}, {'ignore_nan': True}):
                self.assertEqual(json.dumps(NonfiniteFloat(value), **options),
                                 json.dumps(value, **options))
