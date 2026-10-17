import decimal
from unittest import TestCase
import simplejson as json
from simplejson import encoder
from simplejson.tests._helpers import has_speedups

def default_iterable(obj):
    return list(obj)

def make_encoders(markers, item_sort_key=None):
    # Build the Python and (when available) C encoders around one shared
    # markers dict, as JSONEncoder.iterencode would, so tests can inspect
    # the dict after an encode.
    def default(obj):
        if isinstance(obj, ViaDefault):
            return [Unserializable()]
        if isinstance(obj, ClearingViaDefault):
            markers.clear()
            raise ValueError('boom')
        if isinstance(obj, ClearingSafeViaDefault):
            markers.clear()
            return 'safe'
        raise TypeError('not serializable')
    py_encode = encoder._make_iterencode(
        markers, default, encoder.encode_basestring_ascii, None, repr,
        ': ', ', ', False, False, False, True, True, None, item_sort_key,
        'utf-8', True, True, Decimal=decimal.Decimal)
    encoders = [('python', lambda o: ''.join(py_encode(o, 0)))]
    if has_speedups():
        c_encode = encoder.c_make_encoder(
            markers, default, encoder.encode_basestring_ascii, None,
            ': ', ', ', False, False, True, {}, False, True, True,
            None, item_sort_key, 'utf-8', True, False, decimal.Decimal, True)
        encoders.append(('c', lambda o: ''.join(c_encode(o, 0))))
    return encoders

class Unserializable(object):
    pass

class ViaDefault(object):
    # default() converts it to a list holding an Unserializable.
    pass

class ClearingViaDefault(object):
    # default() clears the markers dict, then raises ValueError('boom').
    pass

class ClearingSafeViaDefault(object):
    # default() clears the markers dict, then returns 'safe'.
    pass

class ForJsonList(object):
    def for_json(self):
        return [Unserializable()]

class IterableWithBadItem(object):
    def __iter__(self):
        return iter([1, Unserializable()])

class TestCheckCircular(TestCase):
    def test_circular_dict(self):
        dct = {}
        dct['a'] = dct
        self.assertRaises(ValueError, json.dumps, dct)

    def test_circular_list(self):
        lst = []
        lst.append(lst)
        self.assertRaises(ValueError, json.dumps, lst)

    def test_circular_composite(self):
        dct2 = {}
        dct2['a'] = []
        dct2['a'].append(dct2)
        self.assertRaises(ValueError, json.dumps, dct2)

    def test_circular_default(self):
        json.dumps([set()], default=default_iterable)
        self.assertRaises(TypeError, json.dumps, [set()])

    def test_circular_off_default(self):
        json.dumps([set()], default=default_iterable, check_circular=False)
        self.assertRaises(TypeError, json.dumps, [set()], check_circular=False)

    def test_default_callback_clears_markers(self):
        # Clearing the markers dict from inside a default() callback that
        # then returns makes the marker pop fail with KeyError, rather than
        # releasing the marker's key twice (a use-after-free).
        markers = {}
        for name, encode in make_encoders(markers):
            for value in (ClearingSafeViaDefault(), [ClearingSafeViaDefault()]):
                self.assertRaises(KeyError, encode, value)
                self.assertEqual(markers, {}, name)

    def test_markers_released_after_error(self):
        # A failed encode must not leave markers behind, or an encoder
        # whose markers dict is reused reports a false circular reference.
        markers = {}
        values = [
            [1, Unserializable()],
            {'a': Unserializable()},
            ForJsonList(),
            IterableWithBadItem(),
            Unserializable(),
            ViaDefault(),
            [{'a': [IterableWithBadItem()]}],
        ]
        for name, encode in make_encoders(markers):
            for value in values:
                for attempt in range(2):
                    self.assertRaises(TypeError, encode, value)
                    self.assertEqual(markers, {}, (name, value))

    def test_markers_cleared_during_encoding(self):
        # Removing a marker from under the encoder raises KeyError when it
        # is popped, rather than releasing the marker's key twice.
        markers = {}
        class ClearingIterator(object):
            def __iter__(self):
                return self
            def __next__(self):
                markers.clear()
                raise StopIteration
            next = __next__
        def clearing_sort_key(item):
            markers.clear()
            return item[0]
        for name, encode in make_encoders(markers):
            self.assertRaises(KeyError, encode, ClearingIterator())
            self.assertRaises(KeyError, encode, [ClearingIterator()])
        for name, encode in make_encoders(markers, clearing_sort_key):
            self.assertRaises(KeyError, encode, {'a': 1, 'b': 2})
            self.assertRaises(KeyError, encode, [{'a': 1, 'b': 2}])

    def test_markers_cleared_before_error(self):
        # The error that stopped the encode propagates, not a KeyError
        # for the marker that was already removed.
        markers = {}
        class ClearingRaisingIterator(object):
            def __iter__(self):
                return self
            def __next__(self):
                markers.clear()
                raise ValueError('boom')
            next = __next__
        class ClearingRaisingForJson(object):
            def for_json(self):
                return ClearingRaisingIterator()
        for name, encode in make_encoders(markers):
            for value in (ClearingRaisingIterator(),
                          [ClearingRaisingIterator()],
                          {'a': ClearingRaisingIterator()},
                          ClearingRaisingForJson(),
                          [ClearingViaDefault()]):
                with self.assertRaises(ValueError) as cm:
                    encode(value)
                self.assertEqual(str(cm.exception), 'boom', name)
                self.assertEqual(markers, {}, name)
