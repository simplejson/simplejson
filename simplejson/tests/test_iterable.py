import unittest
from StringIO import StringIO

import simplejson as json

def iter_dumps(obj, **kw):
    return ''.join(json.JSONEncoder(**kw).iterencode(obj))

def sio_dump(obj, **kw):
    sio = StringIO()
    json.dumps(obj, **kw)
    return sio.getvalue()

class TestIterable(unittest.TestCase):
    def test_iterable(self):
        l = [1, 2, 3]
        for dumps in (json.dumps, iter_dumps, sio_dump):
            expect = dumps(l)
            default_expect = dumps(sum(l))
            # Default is False
            self.assertRaises(TypeError, dumps, iter(l))
            self.assertRaises(TypeError, dumps, iter(l), iterable_as_array=False)
            self.assertEqual(expect, dumps(iter(l), iterable_as_array=True))
            # Ensure that the "default" gets called
            self.assertEqual(default_expect, dumps(iter(l), default=sum))
            self.assertEqual(default_expect, dumps(iter(l), iterable_as_array=False, default=sum))
            # Ensure that the "default" does not get called
            self.assertEqual(
                default_expect,
                dumps(iter(l), iterable_as_array=True, default=sum))
        