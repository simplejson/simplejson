# -*- coding: utf-8 -*-
import sys, pickle
import unittest
from unittest import TestCase

import simplejson as json
from simplejson.compat import text_type, b

class TestErrors(TestCase):
    def test_string_keys_error(self):
        data = [{'a': 'A', 'b': (2, 4), 'c': 3.0, ('d',): 'D tuple'}]
        try:
            json.dumps(data)
        except TypeError:
            err = sys.exc_info()[1]
        else:
            self.fail('Expected TypeError')
        self.assertEqual(str(err),
                'keys must be str, int, float, bool or None, not tuple')

    def test_not_serializable(self):
        try:
            json.dumps(json)
        except TypeError:
            err = sys.exc_info()[1]
        else:
            self.fail('Expected TypeError')
        self.assertEqual(str(err),
                'Object of type module is not JSON serializable')

    def test_decode_error(self):
        err = None
        try:
            json.loads('{}\na\nb')
        except json.JSONDecodeError:
            err = sys.exc_info()[1]
        else:
            self.fail('Expected JSONDecodeError')
        self.assertEqual(err.lineno, 2)
        self.assertEqual(err.colno, 1)
        self.assertEqual(err.endlineno, 3)
        self.assertEqual(err.endcolno, 2)

    def test_scan_error(self):
        err = None
        for t in (text_type, b):
            try:
                json.loads(t('{"asdf": "'))
            except json.JSONDecodeError:
                err = sys.exc_info()[1]
            else:
                self.fail('Expected JSONDecodeError')
            self.assertEqual(err.lineno, 1)
            self.assertEqual(err.colno, 10)

    def test_error_is_pickable(self):
        err = None
        try:
            json.loads('{}\na\nb')
        except json.JSONDecodeError:
            err = sys.exc_info()[1]
        else:
            self.fail('Expected JSONDecodeError')
        s = pickle.dumps(err)
        e = pickle.loads(s)

        self.assertEqual(err.msg, e.msg)
        self.assertEqual(err.doc, e.doc)
        self.assertEqual(err.pos, e.pos)
        self.assertEqual(err.end, e.end)

    @unittest.skipIf(sys.version_info < (3, 11), 'add_note requires Python 3.11+')
    def test_add_note_override_preserves_exception(self):
        class NoteError(ValueError):
            def add_note(self, note):
                raise RuntimeError('note failed')

        error = NoteError('original error')

        def default(obj):
            raise error

        for value in (object(), [object()], {'key': object()}):
            try:
                json.dumps(value, default=default)
            except NoteError as exc:
                self.assertIs(exc, error)
            else:
                self.fail('Expected original NoteError')

    @unittest.skipIf(sys.version_info < (3, 11), 'add_note requires Python 3.11+')
    def test_add_note_key_repr_preserves_exception(self):
        class Key(str):
            def __repr__(self):
                raise RuntimeError('repr failed')

        error = ValueError('original error')

        def default(obj):
            raise error

        try:
            json.dumps({Key('key'): object()}, default=default)
        except ValueError as exc:
            self.assertIs(exc, error)
        else:
            self.fail('Expected original ValueError')

    @unittest.skipIf(sys.version_info < (3, 11), 'add_note requires Python 3.11+')
    def test_add_note_type_name_preserves_exception(self):
        class NameErrorType(type):
            def __getattribute__(cls, name):
                if name == '__name__':
                    raise RuntimeError('name failed')
                return type.__getattribute__(cls, name)

        error = ValueError('original error')

        def default(obj):
            raise error

        value = NameErrorType('Value', (object,), {})()
        values = (
            value,
            NameErrorType('List', (list,), {})([value]),
            NameErrorType('Dict', (dict,), {})({'key': value}),
        )
        for value in values:
            try:
                json.dumps(value, default=default)
            except ValueError as exc:
                self.assertIs(exc, error)
            else:
                self.fail('Expected original ValueError')

    @unittest.skipIf(sys.version_info < (3, 11), 'add_note requires Python 3.11+')
    def test_add_note_list_recursion(self):
        x = []
        x.append(x)
        try:
            json.dumps(x)
        except ValueError as exc:
            self.assertEqual(
                exc.__notes__, ['when serializing list item 0'])
        else:
            self.fail('Expected ValueError')

    @unittest.skipIf(sys.version_info < (3, 11), 'add_note requires Python 3.11+')
    def test_add_note_dict_recursion(self):
        x = {}
        x['test'] = x
        try:
            json.dumps(x)
        except ValueError as exc:
            self.assertEqual(
                exc.__notes__, ["when serializing dict item 'test'"])
        else:
            self.fail('Expected ValueError')

    @unittest.skipIf(sys.version_info < (3, 11), 'add_note requires Python 3.11+')
    def test_add_note_nested_error(self):
        try:
            json.dumps({'a': [1, object(), 3]})
        except TypeError as exc:
            self.assertEqual(len(exc.__notes__), 3)
            self.assertEqual(exc.__notes__[0],
                'when serializing object object')
            self.assertEqual(exc.__notes__[1],
                'when serializing list item 1')
            self.assertEqual(exc.__notes__[2],
                "when serializing dict item 'a'")
        else:
            self.fail('Expected TypeError')

    @unittest.skipIf(sys.version_info < (3, 11), 'add_note requires Python 3.11+')
    def test_add_note_uses_type_name(self):
        # Notes name type(obj).__name__, without the module prefix that
        # C types carry in tp_name.
        import collections
        import itertools
        cases = [
            (lambda: json.dumps(collections.OrderedDict(a=object())),
             ['when serializing object object',
              "when serializing OrderedDict item 'a'"]),
            (lambda: json.dumps(itertools.chain()),
             ['when serializing chain object']),
        ]
        for encode, notes in cases:
            with self.assertRaises(TypeError) as cm:
                encode()
            self.assertEqual(cm.exception.__notes__, notes)

    def test_key_error_uses_type_name(self):
        import decimal
        with self.assertRaises(TypeError) as cm:
            json.dumps({decimal.Decimal(1): 1}, use_decimal=False)
        self.assertEqual(
            str(cm.exception),
            'keys must be str, int, float, bool or None, not Decimal')

    def test_type_name_of_class_with_dotted_name(self):
        # A class's __name__ is used as is, even when it contains dots.
        Dotted = type('pkg.Dotted', (object,), {})
        with self.assertRaises(TypeError) as cm:
            json.dumps({Dotted(): 1})
        self.assertEqual(
            str(cm.exception),
            'keys must be str, int, float, bool or None, not pkg.Dotted')
        if sys.version_info >= (3, 11):
            DottedDict = type('pkg.DottedDict', (dict,), {})
            with self.assertRaises(TypeError) as cm:
                json.dumps(DottedDict(a=Dotted()))
            self.assertEqual(cm.exception.__notes__,
                             ['when serializing pkg.Dotted object',
                              "when serializing pkg.DottedDict item 'a'"])

    @unittest.skipIf(sys.version_info < (3,), 'Python 2 class names are bytes')
    def test_type_name_of_class_with_non_ascii_name(self):
        name = 'pkg.Über'
        Uber = type(name, (object,), {})
        with self.assertRaises(TypeError) as cm:
            json.dumps({Uber(): 1})
        self.assertEqual(
            str(cm.exception),
            'keys must be str, int, float, bool or None, not ' + name)

    @unittest.skipIf(sys.version_info < (3, 11), 'add_note requires Python 3.11+')
    def test_add_note_after_asdict_names_the_dict(self):
        import collections
        class D(dict):
            pass
        NT = collections.namedtuple('NT', 'x')
        with self.assertRaises(TypeError) as cm:
            json.dumps(D([('a', NT(1)), ('b', object())]))
        self.assertEqual(cm.exception.__notes__,
                         ['when serializing object object',
                          "when serializing D item 'b'"])

        class NotADict(object):
            def _asdict(self):
                return [1]
        with self.assertRaises(TypeError) as cm:
            json.dumps({'a': NotADict()})
        self.assertEqual(str(cm.exception),
                         '_asdict() must return a dict, not list')
        self.assertEqual(cm.exception.__notes__,
                         ["when serializing dict item 'a'"])
