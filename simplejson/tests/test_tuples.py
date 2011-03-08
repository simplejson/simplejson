import unittest

import simplejson

class TestCustomTuples(unittest.TestCase):
    def test_custom_tuple_failure(self):
        "Test that removing tuple from array_types causes encoding a tuple to fail"
        class CustomEncoder(simplejson.JSONEncoder):
            array_types = (list,)

        assert CustomEncoder().array_types == (list,)

        try:
            result = simplejson.dumps((1,2,3), cls=CustomEncoder)
            print repr(result)
        except TypeError:
            pass
        else:
            self.fail("Unexpected success when parsing a tuple")

    def test_custom_tuple_success(self):
        "Test that you can custom encode a tuple"

        class CustomEncoder(simplejson.JSONEncoder):
            array_types = (list,)

            def default(self, o):
                if isinstance(o, tuple):
                    return dict(__class__='tuple', __data__=list(o))
                else:
                    return simplejson.JSONEncoder.default(self, o)

        result = simplejson.dumps((1,2,3), cls=CustomEncoder)
        expected = simplejson.dumps(dict(__class__='tuple', __data__=[1,2,3]))
        self.assertEqual(result, expected)
