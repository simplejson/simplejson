import unittest
import simplejson as json


class ForJson(object):
    def for_json(self):
        return {'for_json': 1}


class NestedForJson(object):
    def for_json(self):
        return {'nested': ForJson()}


class ForJsonList(object):
    def for_json(self):
        return ['list']


class DictForJson(dict):
    def for_json(self):
        return {'alpha': 1}


class ListForJson(list):
    def for_json(self):
        return ['list']


class TestForJsonWithSpeedups(unittest.TestCase):
    def setUp(self):
        if not json.encoder.c_make_encoder:
            raise unittest.SkipTest("No speedups.")

    @staticmethod
    def _dump(obj):
        return json.dumps(obj, for_json=True)

    def test_for_json_encodes_stand_alone_object(self):
        self.assertEqual(self._dump(ForJson()), '{"for_json": 1}')

    def test_for_json_encodes_object_nested_in_dict(self):
        self.assertEqual(self._dump({'hooray': ForJson()}), '{"hooray": '
                '{"for_json": 1}}')

    def test_for_json_encodes_object_nested_in_list_within_dict(self):
        self.assertEqual(self._dump({'list': [0, ForJson(), 2, 3]}),
                '{"list": [0, {"for_json": 1}, 2, 3]}')

    def test_for_json_encodes_object_nested_within_object(self):
        self.assertEqual(self._dump(NestedForJson()),
                '{"nested": {"for_json": 1}}')

    def test_for_json_encodes_list(self):
        self.assertEqual(self._dump(ForJsonList()), '["list"]')

    def test_for_json_encodes_list_within_object(self):
        self.assertEqual(self._dump({'nested': ForJsonList()}),
                '{"nested": ["list"]}')

    def test_for_json_encodes_dict_subclass(self):
        self.assertEqual(self._dump(DictForJson(a=1)), '{"alpha": 1}')

    def test_for_json_encodes_list_subclass(self):
        self.assertEqual(self._dump(ListForJson(['l'])), '["list"]')

    def tset_for_json_ignored_if_not_true_with_dict_subclass(self):
        self.assertEqual(json.dumps(DictForJson(a=1)), '{"a": 1}')

    def test_for_json_ignored_if_not_true_with_list_subclass(self):
        self.assertEqual(json.dumps(ListForJson(['l'])), '["l"]')

    def test_raises_typeerror_if_for_json_not_true_with_object(self):
        self.assertRaises(TypeError, json.dumps, ForJson())


class TestForJsonWithoutSpeedups(unittest.TestCase):
    def setUp(self):
        if json.encoder.c_make_encoder:
            json._toggle_speedups(False)

    def tearDown(self):
        if json.encoder.c_make_encoder:
            json._toggle_speedups(True)

    @staticmethod
    def _dump(obj):
        return json.dumps(obj, for_json=True)

    def test_for_json_encodes_stand_alone_object(self):
        self.assertEqual(self._dump(ForJson()), '{"for_json": 1}')

    def test_for_json_encodes_object_nested_in_dict(self):
        self.assertEqual(self._dump({'hooray': ForJson()}), '{"hooray": '
                '{"for_json": 1}}')

    def test_for_json_encodes_object_nested_in_list_within_dict(self):
        self.assertEqual(self._dump({'list': [0, ForJson(), 2, 3]}),
                '{"list": [0, {"for_json": 1}, 2, 3]}')

    def test_for_json_encodes_object_nested_within_object(self):
        self.assertEqual(self._dump(NestedForJson()),
                '{"nested": {"for_json": 1}}')

    def test_for_json_encodes_list(self):
        self.assertEqual(self._dump(ForJsonList()), '["list"]')

    def test_for_json_encodes_list_within_object(self):
        self.assertEqual(self._dump({'nested': ForJsonList()}),
                '{"nested": ["list"]}')

    def test_for_json_encodes_dict_subclass(self):
        self.assertEqual(self._dump(DictForJson(a=1)), '{"alpha": 1}')

    def test_for_json_encodes_list_subclass(self):
        self.assertEqual(self._dump(ListForJson(['l'])), '["list"]')

    def tset_for_json_ignored_if_not_true_with_dict_subclass(self):
        self.assertEqual(json.dumps(DictForJson(a=1)), '{"a": 1}')

    def test_for_json_ignored_if_not_true_with_list_subclass(self):
        self.assertEqual(json.dumps(ListForJson(['l'])), '["l"]')

    def test_raises_typeerror_if_for_json_not_true_with_object(self):
        self.assertRaises(TypeError, json.dumps, ForJson())

