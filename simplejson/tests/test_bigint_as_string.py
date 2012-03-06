from unittest import TestCase

import simplejson as json

class TestBigintAsString(TestCase):
    values = [(200, 200), (2**53-1, 9007199254740991), (2**53, '"9007199254740992"'), (2**53+1, '"9007199254740993"'), (-100, -100), (-2**53, -9007199254740992), (-2**53-1, '"-9007199254740993"'), (-2**53+1, -9007199254740991)]

    def test_ints(self):
        for value_pair in self.values:
            self.assertEquals('%s' % value_pair[0], json.dumps(value_pair[0]))
            self.assertEquals('%s' % value_pair[1], json.dumps(value_pair[0], bigint_as_string=True))

    def test_lists(self):
        for value_pair in self.values:
            l = [value_pair[0], value_pair[0]]
            self.assertEquals('[%s, %s]' % (value_pair[0], value_pair[0]), json.dumps(l))
            self.assertEquals('[%s, %s]' % (value_pair[1], value_pair[1]), json.dumps(l, bigint_as_string=True))

    def test_dicts(self):
        for value_pair in self.values:
            d = {'value': value_pair[0]}
            self.assertEquals('{"value": %s}' % value_pair[0], json.dumps(d))
            self.assertEquals('{"value": %s}' % value_pair[1], json.dumps(d, bigint_as_string=True))
