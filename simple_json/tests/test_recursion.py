import simple_json

def test_listrecursion():
    x = []
    x.append(x)
    try:
        simple_json.dumps(x)
    except ValueError:
        pass
    else:
        assert False, "didn't raise ValueError on list recursion"
    x = []
    y = [x]
    x.append(y)
    try:
        simple_json.dumps(x)
    except ValueError:
        pass
    else:
        assert False, "didn't raise ValueError on alternating list recursion"
    y = []
    x = [y, y]
    # ensure that the marker is cleared
    simple_json.dumps(x)

def test_dictrecursion():
    x = {}
    x["test"] = x
    try:
        simple_json.dumps(x)
    except ValueError:
        pass
    else:
        assert False, "didn't raise ValueError on dict recursion"
    x = {}
    y = {"a": x, "b": x}
    # ensure that the marker is cleared
    simple_json.dumps(x)

class TestObject:
    pass

class RecursiveJSONEncoder(simple_json.JSONEncoder):
    recurse = False
    def default(self, o):
        if o is TestObject:
            if self.recurse:
                return [TestObject]
            else:
                return 'TestObject'
        simple_json.JSONEncoder.default(o)

def test_defaultrecursion():
    enc = RecursiveJSONEncoder()
    assert enc.encode(TestObject) == '"TestObject"'
    enc.recurse = True
    try:
        enc.encode(TestObject)
    except ValueError:
        pass
    else:
        assert False, "didn't raise ValueError on default recursion"
