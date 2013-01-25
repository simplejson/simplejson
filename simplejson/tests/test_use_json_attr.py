from unittest import TestCase
import simplejson as json

class TestObject(object):
    def __init__(self, value):
        self.value = value
    def __json__(self):
        return self.value

class TestJsonAttr(TestCase):
    VALUES = (1, 1.01, 'foo', [1, 2, 3, 4], {'one': 1, 'two': 2})
    
    def test_object_encode(self):
        for v in map(TestObject, self.VALUES):
            self.assertEqual(json.dumps(v, use_json_attr=True), str(v.value))

    def test_object_defaults(self):
        obj = TestObject('parrot')
        # use_json_attr=True is the default
        self.assertRaises(TypeError, json.dumps, obj, use_json_attr=False)
        self.assertEqual('parrot', json.dumps(obj))
        self.assertEqual('parrot', json.dumps(obj, use_json_attr=True))
