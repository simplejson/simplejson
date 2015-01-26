from unittest import TestCase

import simplejson as json

# sparse-array
CASE = [
    '[,]',
    '[,0]',
    '[0,]',
    '[,"a"]',
    '[,,,,]',
]

class TestPass4(TestCase):
    def test_parse(self):
        # test in/out equivalence and parsing
        for JSON in CASE:
            res = json.loads(JSON)
            out = json.dumps(res)
            self.assertEqual(res, json.loads(out))

