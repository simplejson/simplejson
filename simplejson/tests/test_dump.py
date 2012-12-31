from unittest import TestCase
from simplejson.compat import StringIO, long_type, b, binary_type, PY3
import simplejson as json

def as_text_type(s):
    if PY3 and isinstance(s, binary_type):
        return s.decode('ascii')
    return s

class TestDump(TestCase):
    def test_dump(self):
        sio = StringIO()
        json.dump({}, sio)
        self.assertEquals(sio.getvalue(), '{}')

    def test_constants(self):
        for c in [None, True, False]:
            self.assert_(json.loads(json.dumps(c)) is c)
            self.assert_(json.loads(json.dumps([c]))[0] is c)
            self.assert_(json.loads(json.dumps({'a': c}))['a'] is c)

    def test_stringify_key(self):
        items = [(b('bytes'), 'bytes'),
                 (1.0, '1.0'),
                 (10, '10'),
                 (True, 'true'),
                 (False, 'false'),
                 (None, 'null'),
                 (long_type(100), '100')]
        for k, expect in items:
            self.assertEquals(
                json.loads(json.dumps({k: expect})),
                {expect: expect})
            self.assertEquals(
                json.loads(json.dumps({k: expect}, sort_keys=True)),
                {expect: expect})
        self.assertRaises(TypeError, json.dumps, {json: 1})
        for v in [{}, {'other': 1}, {b('derp'): 1, 'herp': 2}]:
            for sort_keys in [False, True]:
                v0 = dict(v)
                v0[json] = 1
                v1 = dict((as_text_type(key), val) for (key, val) in v.items())
                self.assertEquals(
                    json.loads(json.dumps(v0, skipkeys=True, sort_keys=sort_keys)),
                    v1)
                self.assertEquals(
                    json.loads(json.dumps({'': v0}, skipkeys=True, sort_keys=sort_keys)),
                    {'': v1})
                self.assertEquals(
                    json.loads(json.dumps([v0], skipkeys=True, sort_keys=sort_keys)),
                    [v1])

    def test_dumps(self):
        self.assertEquals(json.dumps({}), '{}')

    def test_encode_truefalse(self):
        self.assertEquals(json.dumps(
                 {True: False, False: True}, sort_keys=True),
                 '{"false": true, "true": false}')
        self.assertEquals(
            json.dumps(
                {2: 3.0,
                 4.0: long_type(5),
                 False: 1,
                 long_type(6): True,
                 "7": 0},
                sort_keys=True),
            '{"2": 3.0, "4.0": 5, "6": true, "7": 0, "false": 1}')

    def test_ordered_dict(self):
        # http://bugs.python.org/issue6105
        items = [('one', 1), ('two', 2), ('three', 3), ('four', 4), ('five', 5)]
        s = json.dumps(json.OrderedDict(items))
        self.assertEqual(
            s,
            '{"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}')

    def test_indent_unknown_type_acceptance(self):
        """
        A test against the regression mentioned at `github issue 29`_.

        The indent parameter should accept any type which pretends to be
        an instance of int or long when it comes to being multiplied by
        strings, even if it is not actually an int or long, for
        backwards compatibility.

        .. _github issue 29:
           http://github.com/simplejson/simplejson/issue/29
        """

        class AwesomeInt(object):
            """An awesome reimplementation of integers"""

            def __init__(self, *args, **kwargs):
                if len(args) > 0:
                    # [construct from literals, objects, etc.]
                    # ...

                    # Finally, if args[0] is an integer, store it
                    if isinstance(args[0], int):
                        self._int = args[0]

            # [various methods]

            def __mul__(self, other):
                # [various ways to multiply AwesomeInt objects]
                # ... finally, if the right-hand operand is not awesome enough,
                # try to do a normal integer multiplication
                if hasattr(self, '_int'):
                    return self._int * other
                else:
                    raise NotImplementedError("To do non-awesome things with"
                        " this object, please construct it from an integer!")

        s = json.dumps([0, 1, 2], indent=AwesomeInt(3))
        self.assertEqual(s, '[\n   0,\n   1,\n   2\n]')
