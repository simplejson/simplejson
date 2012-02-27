from unittest import TestCase
from cStringIO import StringIO

import simplejson as json

class TestDump(TestCase):
    def test_dump(self):
        sio = StringIO()
        json.dump({}, sio)
        self.assertEquals(sio.getvalue(), '{}')

    def test_dumps(self):
        self.assertEquals(json.dumps({}), '{}')

    def test_encode_truefalse(self):
        self.assertEquals(json.dumps(
                 {True: False, False: True}, sort_keys=True),
                 '{"false": true, "true": false}')
        self.assertEquals(json.dumps(
                {2: 3.0, 4.0: 5L, False: 1, 6L: True, "7": 0}, sort_keys=True),
                '{"false": 1, "2": 3.0, "4.0": 5, "6": true, "7": 0}')

    def test_ordered_dict(self):
        # http://bugs.python.org/issue6105
        items = [('one', 1), ('two', 2), ('three', 3), ('four', 4), ('five', 5)]
        s = json.dumps(json.OrderedDict(items))
        self.assertEqual(s, '{"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}')

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

        s = json.dumps(range(3), indent=AwesomeInt(3))
        self.assertEqual(s, '[\n   0,\n   1,\n   2\n]')
