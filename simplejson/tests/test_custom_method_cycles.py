import sys
from unittest import TestCase, skipIf

import simplejson as json


class ForJson:
    def __init__(self, value=None):
        self.value = value

    def for_json(self):
        return self.value


class AsDict:
    def _asdict(self):
        return {'self': self}


class TestCustomMethodCycles(TestCase):
    def assert_circular(self, value):
        with self.assertRaises(ValueError) as exc:
            json.dumps(value, for_json=True)
        self.assertEqual(str(exc.exception), 'Circular reference detected')

    def test_direct_for_json_cycle(self):
        value = ForJson()
        value.value = value
        self.assert_circular(value)

    def test_indirect_for_json_cycle(self):
        first = ForJson()
        second = ForJson(first)
        first.value = second
        self.assert_circular(first)

    def test_for_json_cycle_in_list(self):
        value = ForJson()
        value.value = value
        self.assert_circular([value])

    def test_for_json_cycle_in_dict(self):
        value = ForJson()
        value.value = value
        self.assert_circular({'value': value})

    def test_asdict_cycle(self):
        self.assert_circular(AsDict())

    def test_asdict_cycle_in_list(self):
        self.assert_circular([AsDict()])

    def test_asdict_cycle_in_dict(self):
        self.assert_circular({'value': AsDict()})

    def test_repeated_reference_is_not_a_cycle(self):
        value = ForJson({'x': 1})
        self.assertEqual(
            json.loads(json.dumps([value, value], for_json=True)),
            [{'x': 1}, {'x': 1}])

    def test_acyclic_chain(self):
        self.assertEqual(json.loads(json.dumps(ForJson(ForJson(1)), for_json=True)), 1)

    @skipIf(sys.platform == 'emscripten',
            'Pyodide cannot recover from unbounded recursion')
    def test_circular_checks_can_be_disabled(self):
        value = ForJson()
        value.value = value
        with self.assertRaises(RuntimeError):
            json.dumps(value, for_json=True, check_circular=False)
