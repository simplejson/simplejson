import glob
import json as stdlib_json
import os
import re
import unittest

import simplejson as json


VECTOR_DIR = os.path.join(os.path.dirname(__file__), 'JSONTestSuite')
SUITES = ('test_parsing', 'test_transform')
EXPECTED_COUNTS = {'test_parsing': 318, 'test_transform': 22}


def _canonical_json(value):
    return stdlib_json.dumps(value, sort_keys=True, separators=(',', ':'))


try:
    _RECURSION_ERROR = RecursionError
except NameError:
    _RECURSION_ERROR = RuntimeError


def _make_test(suite, path):
    case = os.path.basename(path)

    def test(self):
        with open(path, 'rb') as vector:
            source = vector.read()

        try:
            value = json.loads(source)
        except _RECURSION_ERROR:
            if suite == 'test_parsing' and case.startswith('y_'):
                self.fail('Expected valid JSON in %s' % (case,))
            self.skipTest(
                'Input nesting follows Python interpreter limits '
                '(index.rst, Implementation Limitations).')
        except ValueError:
            if suite == 'test_parsing' and case.startswith('y_'):
                self.fail('Expected valid JSON in %s' % (case,))
            return

        if suite == 'test_parsing' and case.startswith('n_'):
            self.fail('Expected invalid JSON in %s' % (case,))
        if suite == 'test_parsing' and case.startswith('y_'):
            expected = stdlib_json.loads(source)
            self.assertEqual(
                _canonical_json(value), _canonical_json(expected))
        if suite == 'test_transform':
            self.assertEqual(value, json.loads(json.dumps(value)))
            try:
                expected = stdlib_json.loads(source)
            except ValueError:
                pass
            else:
                self.assertEqual(
                    _canonical_json(value), _canonical_json(expected))

    return test


class TestJSONTestSuite(unittest.TestCase):
    pass


if not os.path.isdir(VECTOR_DIR):
    def _vectors_unavailable(self):
        self.skipTest(
            'JSONTestSuite vectors are omitted from wheels; '
            'run this test from a source checkout.')

    TestJSONTestSuite.test_vectors_unavailable = _vectors_unavailable
else:
    _index = 0
    for _suite in SUITES:
        _suite_dir = os.path.join(VECTOR_DIR, _suite)
        _paths = sorted(glob.glob(os.path.join(_suite_dir, '*.json')))
        if not os.path.isdir(_suite_dir) or len(_paths) != EXPECTED_COUNTS[_suite]:
            raise RuntimeError(
                'Incomplete JSONTestSuite vectors in %s: expected %d files, '
                'found %d' % (_suite_dir, EXPECTED_COUNTS[_suite], len(_paths)))
        for _path in _paths:
            _case_name = os.path.splitext(os.path.basename(_path))[0]
            _case_name = re.sub('[^A-Za-z0-9_]', '_', _case_name)
            _test_name = 'test_%03d_%s_%s' % (_index, _suite, _case_name)
            setattr(TestJSONTestSuite, _test_name, _make_test(_suite, _path))
            _index += 1
