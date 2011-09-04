import unittest
import simplejson
try:
    from collections import namedtuple
except ImportError:
    namedtuple = None

@unittest.skipUnless(namedtuple, "namedtuple tests can only be run if the namedtuple function is available")
class TestNamedTuples(unittest.TestCase):
    def test_namedtuple(self):
        Point = namedtuple("Point", ['x', 'y'])
        point_dict = {'x': 5, 'y': 7}
        point_tuple = Point(**point_dict)

        # It would be nice if we could just compare the results of simplejson.dumps
        # for these two objects, but since dicts do not have a defined ordering,
        # they could come out different but equally valid. Instead, we'll manually
        # define all possibile reorderings and test to be sure that the result is
        # in that list.
        possibilities = ['{"y": 7, "x": 5}', '{"x": 5, "y": 7}']

        # quick sanity check to be sure that simplejson.dumps is behaving as we expect
        dict_json = simplejson.dumps(point_dict)
        self.assertIn(dict_json, possibilities, "sanity check failed")

        # and now, the actual test
        tuple_json = simplejson.dumps(point_tuple)
        self.assertIn(tuple_json, possibilities, 
                "namedtuple JSON does not match dict JSON")

    def test_nested_namedtuple(self):
        Point = namedtuple("Point", ['x', 'y'])
        point = Point(1, 2)

        dictnested = {'outer': point}
        possibilities = ['{"outer": {"x": 1, "y": 2}}', '{"outer": {"y": 2, "x": 1}}']
        self.assertIn(simplejson.dumps(dictnested), possibilities,
                "namedtuple nested in dict serialized incorrectly")

        listnested = [1, 2, 3, point]
        possibilities = ['[1, 2, 3, {"x": 1, "y": 2}]', '[1, 2, 3, {"y": 2, "x": 1}}']
        self.assertIn(simplejson.dumps(listnested), possibilities,
                "namedtuple nested in list serialized incorrectly")
