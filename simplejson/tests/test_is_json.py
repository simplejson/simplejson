import unittest
import simplejson as json


class json_str(str):
    is_json = True

dct1 = {
    'key1': 'value1'
}

dct2 = {
    'key2': 'value2',
    'd1': dct1
}

dct3 = {
    'key2': 'value2',
    'd1': json_str(json.dumps(dct1))
}


class TestIsJson(unittest.TestCase):

    def test_is_json_ignored_by_default(self):
        self.assertNotEqual(json.dumps(dct2), json.dumps(dct3))

    def test_is_json(self):
        self.assertEqual(json.dumps(dct2), json.dumps(dct3, is_json=True))
