from unittest import TestCase

import simplejson as json

class TestBigintAsString(TestCase):
    values = [(200, 200),
              ((2 ** 53) - 1, 9007199254740991),
              ((2 ** 53), '9007199254740992'),
              ((2 ** 53) + 1, '9007199254740993'),
              (-100, -100),
              ((-2 ** 53), '-9007199254740992'),
              ((-2 ** 53) - 1, '-9007199254740993'),
              ((-2 ** 53) + 1, -9007199254740991)]

    def test_ints(self):
        for val, expect in self.values:
            self.assertEquals(
                val,
                json.loads(json.dumps(val)))
            self.assertEquals(
                expect,
                json.loads(json.dumps(val, bigint_as_string=True)))

    def test_lists(self):
        for val, expect in self.values:
            val = [val, val]
            expect = [expect, expect]
            self.assertEquals(
                val,
                json.loads(json.dumps(val)))
            self.assertEquals(
                expect,
                json.loads(json.dumps(val, bigint_as_string=True)))

    def test_dicts(self):
        for val, expect in self.values:
            val = {'k': val}
            expect = {'k': expect}
            self.assertEquals(
                val,
                json.loads(json.dumps(val)))
            self.assertEquals(
                expect,
                json.loads(json.dumps(val, bigint_as_string=True)))

    def test_dict_keys(self):
        for val, _ in self.values:
            expect = {str(val): 'value'}
            val = {val: 'value'}
            self.assertEquals(
                expect,
                json.loads(json.dumps(val)))
            self.assertEquals(
                expect,
                json.loads(json.dumps(val, bigint_as_string=True)))
