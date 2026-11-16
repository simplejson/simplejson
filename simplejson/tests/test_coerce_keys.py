# Resolve Decimal at runtime because test_decimal reloads its module.
import decimal
from operator import itemgetter
from unittest import TestCase

import simplejson as json
from simplejson.compat import PY3, StringIO, b, long_type, text_type


class DictSubclass(dict):
    pass


class StringSubclass(text_type):
    def __str__(self):
        raise AssertionError('string keys must not be coerced')


class TestCoerceKeys(TestCase):
    def options(self):
        for indent in (None, 2):
            for sorting in ({}, {'sort_keys': True}, {'item_sort_key': itemgetter(0)}):
                options = dict(sorting, indent=indent)
                yield options

    def test_rejects_nonstring_keys_in_all_container_paths(self):
        keys = (1, long_type(2 ** 65), 1.5, True, False, None,
                decimal.Decimal('1.1'), (1,), object())
        for options in self.options():
            encoder = json.JSONEncoder(coerce_keys=False, **options)
            for key in keys:
                for container in (dict, DictSubclass, json.OrderedDict):
                    value = container([(key, 'value')])
                    for nested in (value, [value], {'nested': value}):
                        with self.assertRaises(TypeError) as error:
                            encoder.encode(nested)
                        self.assertIn('coerce_keys is False', str(error.exception))

    def test_public_encoding_entry_points(self):
        value = {'nested': {'1': 'string', 1: 'integer'}}
        encoder = json.JSONEncoder(coerce_keys=False)
        for encode in (encoder.encode,
                       lambda obj: ''.join(encoder.iterencode(obj)),
                       lambda obj: json.dumps(obj, coerce_keys=False),
                       lambda obj: json.dump(obj, StringIO(), coerce_keys=False)):
            with self.assertRaises(TypeError) as error:
                encode(value)
            self.assertIn('coerce_keys is False', str(error.exception))
        # Reusing an encoder after rejection must not retain circular markers.
        self.assertEqual(encoder.encode({'valid': 1}), '{"valid": 1}')

    def test_default_coercion_is_unchanged(self):
        value = json.OrderedDict([('1', 'string'), (1, 'integer')])
        for options in self.options():
            self.assertEqual(json.dumps(value, coerce_keys=True, **options),
                             json.dumps(value, **options))
        self.assertEqual(json.loads(json.dumps(value), object_pairs_hook=list),
                         [('1', 'string'), ('1', 'integer')])

    def test_skipkeys_filters_before_encoding_values_or_sorting(self):
        class Unencodable(object):
            pass

        pairs = [('keep', 1), (1, Unencodable()), (None, Unencodable()),
                 (decimal.Decimal('2.5'), Unencodable())]
        for options in self.options():
            for container in (dict, DictSubclass, json.OrderedDict):
                value = container(pairs)
                text = json.dumps(value, coerce_keys=False, skipkeys=True, **options)
                self.assertEqual(json.loads(text), {'keep': 1})
                text = json.dumps(container(pairs[1:]), coerce_keys=False,
                                  skipkeys=True, **options)
                self.assertEqual(json.loads(text), {})

        seen = []

        def sort_item(item):
            seen.append(item[0])
            return item[0]

        self.assertEqual(json.dumps(dict(pairs), coerce_keys=False, skipkeys=True,
                                    item_sort_key=sort_item), '{"keep": 1}')
        self.assertEqual(seen, ['keep'])

    def test_string_keys_and_values_preserved(self):
        value = {StringSubclass('key'): [None, True, 1, 1.5, decimal.Decimal('2.5')]}
        for options in self.options():
            self.assertEqual(json.dumps(value, coerce_keys=False, **options),
                             json.dumps(value, **options))
        for obj in (None, 1, 1.5, [True, False], 'value'):
            self.assertEqual(json.dumps(obj, coerce_keys=False), json.dumps(obj))

    def test_encoded_string_keys_keep_encoding_rules(self):
        for options in self.options():
            self.assertEqual(
                json.dumps({b('\xa4'): 1}, coerce_keys=False,
                           encoding='iso-8859-15', **options),
                json.dumps({u'\u20ac': 1}, **options))
            self.assertRaises(UnicodeDecodeError, json.dumps, {b('\xff'): 1},
                              coerce_keys=False, **options)
            if PY3:
                self.assertRaises(TypeError, json.dumps, {b('key'): 1},
                                  coerce_keys=False, encoding=None, **options)
                self.assertEqual(json.loads(json.dumps(
                    {b('key'): 1}, coerce_keys=False, encoding=None,
                    skipkeys=True, **options)), {})

    def test_nonfinite_keys_are_rejected_before_float_options(self):
        for options in ({}, {'allow_nan': True}, {'ignore_nan': True}):
            encoder = json.JSONEncoder(coerce_keys=False, **options)
            for key in (float('nan'), float('inf'),
                        decimal.Decimal('NaN'), decimal.Decimal('Infinity')):
                with self.assertRaises(TypeError) as error:
                    encoder.encode({key: 1})
                self.assertIn('coerce_keys is False', str(error.exception))
                self.assertEqual(json.dumps({key: 1}, coerce_keys=False,
                                            skipkeys=True, **options), '{}')

    def test_default_and_for_json_results_obey_key_policy(self):
        class Value(object):
            def for_json(self):
                return {1: 'value'}

        for options in ({'default': lambda value: {1: 'value'}}, {'for_json': True}):
            encoder = json.JSONEncoder(coerce_keys=False, **options)
            with self.assertRaises(TypeError) as error:
                encoder.encode([Value()])
            self.assertIn('coerce_keys is False', str(error.exception))
            self.assertEqual(json.dumps([Value()], coerce_keys=False,
                                        skipkeys=True, **options), '[{}]')

    def test_option_truth_value_errors_propagate(self):
        class BadBool(object):
            def __bool__(self):
                raise ZeroDivisionError('invalid coerce_keys')

            __nonzero__ = __bool__

        self.assertRaises(ZeroDivisionError, json.dumps, {}, coerce_keys=BadBool())
