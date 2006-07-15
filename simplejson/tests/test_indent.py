


def test_indent():
    import simplejson
    
    h = [['blorpie'], ['whoops'], [], 'd-shtaeou', 'd-nthiouh', 'i-vhbjkhnth',
         {'nifty': 87}, {'field': 'yes', 'morefield': False} ]


    d1 = simplejson.dumps(h)
    d2 = simplejson.dumps(h, indent=2)

    h1 = simplejson.loads(d1)
    h2 = simplejson.loads(d2)

    assert h1 == h
    assert h2 == h
