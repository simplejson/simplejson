from unittest import TestCase
from simplejson.compat import StringIO, long_type, PY3

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
        # strs and floats can't be compared on Python 3, so make all keys strings.
        if not PY3:
            d = {2: 3.0, 4.0: long_type(5), False: 1, long_type(6): True, "7": 0}
            expected = '{"false": 1, "2": 3.0, "4.0": 5, "6": true, "7": 0}'
        else:
            d = {'2': 3.0, '4.0': long_type(5), 'false': 1, str(long_type(6)): True, "7": 0}
            expected = '{"2": 3.0, "4.0": 5, "6": true, "7": 0, "false": 1}'
        self.assertEquals(json.dumps(d, sort_keys=True), expected)

    def test_ordered_dict(self):
        # http://bugs.python.org/issue6105
        items = [('one', 1), ('two', 2), ('three', 3), ('four', 4), ('five', 5)]
        s = json.dumps(json.OrderedDict(items))
        self.assertEqual(s, '{"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}')
