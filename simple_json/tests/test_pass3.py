# from http://json.org/JSON_checker/test/pass3.json
JSON = r'''
{
    "JSON Test Pattern pass3": {
        "The outermost value": "must be an object or array.",
        "In this test": "It is an object."
    }
}
'''

def test_parse():
    # test in/out equivalence and parsing
    import simple_json
    res = simple_json.loads(JSON)
    out = simple_json.dumps(res)
    assert res == simple_json.loads(out)
