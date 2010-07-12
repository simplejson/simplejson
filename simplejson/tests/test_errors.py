from unittest import TestCase

import simplejson as json

class TestErrors(TestCase):
    def test_decode_error(self):
        err = None
        try:
            json.loads('{}\na\nb')
        except json.JSONDecodeError, e:
            err = e
        else:
            self.fail('Expected JSONDecodeError')
        self.assertEquals(err.lineno, 2)
        self.assertEquals(err.colno, 1)
        self.assertEquals(err.endlineno, 3)
        self.assertEquals(err.endcolno, 2)
