# from http://json.org/JSON_checker/test/pass2.json
JSON = r'''
[[[[[[[[[[[[[[[[[[["Not too deep"]]]]]]]]]]]]]]]]]]]
'''

def test_parse():
    # test in/out equivalence and parsing
    import simple_json
    res = simple_json.loads(JSON)
    out = simple_json.dumps(res)
    assert res == simple_json.loads(out)
