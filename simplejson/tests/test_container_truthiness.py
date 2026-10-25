from __future__ import absolute_import

import unittest

import simplejson as json
from simplejson.compat import StringIO


class FalseTruth(object):
    def __bool__(self):
        return False

    __nonzero__ = __bool__


class RaisingTruth(object):
    def __bool__(self):
        raise AssertionError('container truth value must not be inspected')

    __nonzero__ = __bool__


class TrueTruth(object):
    def __bool__(self):
        return True

    __nonzero__ = __bool__


def container_types(mixin):
    return [type(mixin.__name__ + base.__name__, (mixin, base), {})
            for base in (list, tuple, dict)]


def encode(value, mode, **options):
    if mode == 'dump':
        stream = StringIO()
        json.dump(value, stream, **options)
        return stream.getvalue()
    if mode == 'iterencode':
        return ''.join(json.JSONEncoder(**options).iterencode(value))
    return json.dumps(value, **options)


class TestContainerTruthiness(unittest.TestCase):
    def assertEncodings(self, value, expected):
        for indent in (None, 0, 2, '\t'):
            for circular in (True, False):
                options = dict(indent=indent, check_circular=circular)
                text = json.dumps(expected, **options)
                for mode in ('dumps', 'dump', 'iterencode'):
                    actual = encode(value, mode, **options)
                    self.assertEqual(actual, text)
                    self.assertEqual(json.loads(actual), expected)

    def test_nonempty_false_containers_keep_their_contents(self):
        for cls, value in zip(container_types(FalseTruth),
                              ([1, 2], (1, 2), {'a': 1, 'b': 2})):
            obj = cls(value)
            expected = list(value) if not isinstance(value, dict) else value
            self.assertEncodings(obj, expected)
            self.assertEncodings([obj], [expected])
            self.assertEncodings({'value': obj}, {'value': expected})

    def test_container_truth_errors_are_not_serialization_errors(self):
        for cls, value in zip(container_types(RaisingTruth),
                              ([1, 2], (1, 2), {'a': 1, 'b': 2})):
            obj = cls(value)
            expected = list(value) if not isinstance(value, dict) else value
            self.assertEncodings(obj, expected)
            self.assertEncodings([obj], [expected])
            self.assertEncodings({'value': obj}, {'value': expected})

    def test_empty_true_containers_keep_compact_empty_format(self):
        for cls, value in zip(container_types(TrueTruth), ([], (), {})):
            expected = [] if not isinstance(value, dict) else {}
            self.assertEncodings(cls(value), expected)

    def test_false_container_cycles_are_detected(self):
        list_type, tuple_type, dict_type = container_types(FalseTruth)
        sequence = list_type()
        sequence.append(sequence)
        mapping = dict_type()
        mapping['self'] = mapping
        child = []
        tuple_value = tuple_type([child])
        child.append(tuple_value)
        for value in (sequence, mapping, tuple_value):
            for indent in (None, 2):
                for mode in ('dumps', 'dump', 'iterencode'):
                    with self.assertRaises(ValueError) as caught:
                        encode(value, mode, indent=indent)
                    self.assertEqual(str(caught.exception),
                                     'Circular reference detected')
        self.assertEncodings([1, 2], [1, 2])

    def test_repeated_false_container_is_not_a_cycle(self):
        for cls, value in zip(container_types(FalseTruth),
                              ([1], (1,), {'a': 1})):
            obj = cls(value)
            expected = list(value) if not isinstance(value, dict) else value
            self.assertEncodings([obj, obj], [expected, expected])

    def test_custom_conversion_results_keep_false_containers(self):
        class Custom(object):
            def __init__(self, value):
                self.value = value

            def for_json(self):
                return self.value

        for cls, value in zip(container_types(FalseTruth),
                              ([1, 2], (1, 2), {'a': 1})):
            obj = Custom(cls(value))
            expected = list(value) if not isinstance(value, dict) else value
            for indent in (None, 2):
                for mode in ('dumps', 'dump', 'iterencode'):
                    for options in ({'for_json': True},
                                    {'default': lambda o: o.value}):
                        self.assertEqual(
                            json.loads(encode(obj, mode, indent=indent,
                                              **options)), expected)

    def test_length_overrides_do_not_discard_contents(self):
        for mixin in (object, TrueTruth):
            for base, value in ((list, [1, 2]), (tuple, (1, 2)),
                                (dict, {'a': 1, 'b': 2})):
                bases = (base,) if mixin is object else (mixin, base)
                cls = type('ZeroLength' + base.__name__, bases,
                           {'__len__': lambda self: 0})
                expected = list(value) if base is not dict else value
                self.assertEncodings(cls(value), expected)

    def test_length_errors_do_not_override_container_contents(self):
        def invalid_length(self):
            raise AssertionError('container length hook must not be inspected')

        for mixin in (object, TrueTruth):
            for base, value in ((list, [1, 2]), (tuple, (1, 2)),
                                (dict, {'a': 1, 'b': 2})):
                bases = (base,) if mixin is object else (mixin, base)
                cls = type('RaisingLength' + base.__name__, bases,
                           {'__len__': invalid_length})
                expected = list(value) if base is not dict else value
                self.assertEncodings(cls(value), expected)

    def test_exact_container_check_does_not_compare_subclass_types(self):
        class NoEquality(type):
            def __eq__(cls, other):
                raise AssertionError('container types must not be compared')

        for base, value in ((list, [1]), (tuple, (1,)), (dict, {'a': 1})):
            cls = NoEquality('NoEquality' + base.__name__, (base,), {})
            expected = list(value) if base is not dict else value
            self.assertEncodings(cls(value), expected)

    def test_subclass_iteration_matches_native(self):
        class OtherList(list):
            def __iter__(self):
                return iter([7, 8])

        class OtherTuple(tuple):
            def __iter__(self):
                return iter([7, 8])

        class OtherDict(dict):
            def items(self):
                return [('chosen', 3)]

            iteritems = items

        self.assertEncodings(OtherList([1, 2]), [7, 8])
        self.assertEncodings(OtherList(), [7, 8])
        self.assertEncodings(OtherTuple((1, 2)), [7, 8])
        self.assertEncodings(OtherTuple(), [7, 8])
        self.assertEncodings(OtherDict(ignored=1), {'chosen': 3})
        self.assertEncodings(OtherDict(), {})
