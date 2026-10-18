from unittest import TestCase

import simplejson as json
from operator import itemgetter
from simplejson.compat import StringIO

class TestItemSortKey(TestCase):
    def test_simple_first(self):
        a = {'a': 1, 'c': 5, 'jack': 'jill', 'pick': 'axe', 'array': [1, 5, 6, 9], 'tuple': (83, 12, 3), 'crate': 'dog', 'zeak': 'oh'}
        self.assertEqual(
            '{"a": 1, "c": 5, "crate": "dog", "jack": "jill", "pick": "axe", "zeak": "oh", "array": [1, 5, 6, 9], "tuple": [83, 12, 3]}',
            json.dumps(a, item_sort_key=json.simple_first))

    def test_case(self):
        a = {'a': 1, 'c': 5, 'Jack': 'jill', 'pick': 'axe', 'Array': [1, 5, 6, 9], 'tuple': (83, 12, 3), 'crate': 'dog', 'zeak': 'oh'}
        self.assertEqual(
            '{"Array": [1, 5, 6, 9], "Jack": "jill", "a": 1, "c": 5, "crate": "dog", "pick": "axe", "tuple": [83, 12, 3], "zeak": "oh"}',
            json.dumps(a, item_sort_key=itemgetter(0)))
        self.assertEqual(
            '{"a": 1, "Array": [1, 5, 6, 9], "c": 5, "crate": "dog", "Jack": "jill", "pick": "axe", "tuple": [83, 12, 3], "zeak": "oh"}',
            json.dumps(a, item_sort_key=lambda kv: kv[0].lower()))

    def test_item_sort_key_value(self):
        # https://github.com/simplejson/simplejson/issues/173
        a = {'a': 1, 'b': 0}
        self.assertEqual(
            '{"b": 0, "a": 1}',
            json.dumps(a, item_sort_key=lambda kv: kv[1]))


class FalseSortKey(dict):
    def __call__(self, item):
        return -item[1]


class TruthValueErrorSortKey(FalseSortKey):
    def __bool__(self):
        raise AssertionError("sorting callback truth value must not be tested")

    __nonzero__ = __bool__


class TestExplicitItemSortKey(TestCase):
    def test_callable_presence_does_not_depend_on_truth_value(self):
        value = {'a': 1, 'b': 2}
        expected = '{"b": 2, "a": 1}'
        for key_type in (FalseSortKey, TruthValueErrorSortKey):
            for sort_keys in (False, True):
                key = key_type()
                self.assertEqual(
                    json.dumps(value, item_sort_key=key, sort_keys=sort_keys),
                    expected)
                output = StringIO()
                json.dump(value, output, item_sort_key=key, sort_keys=sort_keys)
                self.assertEqual(output.getvalue(), expected)
                encoder = json.JSONEncoder(item_sort_key=key, sort_keys=sort_keys)
                self.assertEqual(encoder.encode(value), expected)
                self.assertEqual(''.join(encoder.iterencode(value)), expected)

    def test_false_valued_noncallable_is_rejected(self):
        for value in (False, 0, '', [], {}):
            self.assertRaises(TypeError, json.dumps, {'a': 1}, item_sort_key=value)

    def test_false_valued_sort_key_with_nested_and_skipped_keys(self):
        value = [{None: 2, 'b': 3, 1: 4, (1,): 1}]
        self.assertEqual(
            json.dumps(value, item_sort_key=FalseSortKey(), skipkeys=True),
            '[{"1": 4, "b": 3, "null": 2}]')
