from unittest import TestCase

import simplejson as json
from simplejson.compat import text_type, b, u, unichr

class TestUnicode(TestCase):
    def test_encoding1(self):
        encoder = json.JSONEncoder(encoding='utf-8')
        uu = u('\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}')
        s = uu.encode('utf-8')
        ju = encoder.encode(uu)
        js = encoder.encode(s)
        self.assertEquals(ju, js)

    def test_encoding2(self):
        uu = u('\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}')
        s = uu.encode('utf-8')
        ju = json.dumps(uu, encoding='utf-8')
        js = json.dumps(s, encoding='utf-8')
        self.assertEquals(ju, js)

    def test_encoding3(self):
        uu = u('\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}')
        j = json.dumps(uu)
        self.assertEquals(j, '"\\u03b1\\u03a9"')

    def test_encoding4(self):
        uu = u('\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}')
        j = json.dumps([uu])
        self.assertEquals(j, '["\\u03b1\\u03a9"]')

    def test_encoding5(self):
        uu = u('\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}')
        j = json.dumps(uu, ensure_ascii=False)
        self.assertEquals(j, u('"') + uu + u('"'))

    def test_encoding6(self):
        uu = u('\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}')
        j = json.dumps([uu], ensure_ascii=False)
        self.assertEquals(j, u('["') + uu + u('"]'))

    def test_big_unicode_encode(self):
        uu = u('\U0001d120')
        self.assertEquals(json.dumps(uu), '"\\ud834\\udd20"')
        self.assertEquals(json.dumps(uu, ensure_ascii=False), u('"\U0001d120"'))

    def test_big_unicode_decode(self):
        uu = u('z\U0001d120x')
        self.assertEquals(json.loads('"' + uu + '"'), uu)
        self.assertEquals(json.loads('"z\\ud834\\udd20x"'), uu)

    def test_unicode_decode(self):
        for i in range(0, 0xd7ff):
            uu = unichr(i)
            #s = '"\\u{0:04x}"'.format(i)
            s = '"\\u%04x"' % (i,)
            self.assertEquals(json.loads(s), uu)

    def test_object_pairs_hook_with_unicode(self):
        s = u('{"xkd":1, "kcw":2, "art":3, "hxm":4, "qrt":5, "pad":6, "hoy":7}')
        p = [(u("xkd"), 1), (u("kcw"), 2), (u("art"), 3), (u("hxm"), 4),
             (u("qrt"), 5), (u("pad"), 6), (u("hoy"), 7)]
        self.assertEqual(json.loads(s), eval(s))
        self.assertEqual(json.loads(s, object_pairs_hook=lambda x: x), p)
        od = json.loads(s, object_pairs_hook=json.OrderedDict)
        self.assertEqual(od, json.OrderedDict(p))
        self.assertEqual(type(od), json.OrderedDict)
        # the object_pairs_hook takes priority over the object_hook
        self.assertEqual(json.loads(s,
                                    object_pairs_hook=json.OrderedDict,
                                    object_hook=lambda x: None),
                         json.OrderedDict(p))


    def test_default_encoding(self):
        self.assertEquals(json.loads(u('{"a": "\xe9"}').encode('utf-8')),
            {'a': u('\xe9')})

    def test_unicode_preservation(self):
        self.assertEquals(type(json.loads(u('""'))), text_type)
        self.assertEquals(type(json.loads(u('"a"'))), text_type)
        self.assertEquals(type(json.loads(u('["a"]'))[0]), text_type)

    def test_ensure_ascii_false_returns_unicode(self):
        # http://code.google.com/p/simplejson/issues/detail?id=48
        self.assertEquals(type(json.dumps([], ensure_ascii=False)), text_type)
        self.assertEquals(type(json.dumps(0, ensure_ascii=False)), text_type)
        self.assertEquals(type(json.dumps({}, ensure_ascii=False)), text_type)
        self.assertEquals(type(json.dumps("", ensure_ascii=False)), text_type)

    def test_ensure_ascii_false_bytestring_encoding(self):
        # http://code.google.com/p/simplejson/issues/detail?id=48
        doc1 = {u('quux'): b('Arr\xc3\xaat sur images')}
        doc2 = {u('quux'): u('Arr\xeat sur images')}
        doc_ascii = '{"quux": "Arr\\u00eat sur images"}'
        doc_unicode = u('{"quux": "Arr\xeat sur images"}')
        #import pdb; pdb.set_trace()
        self.assertEquals(json.dumps(doc1), doc_ascii)
        self.assertEquals(json.dumps(doc2), doc_ascii)
        self.assertEquals(json.dumps(doc1, ensure_ascii=False), doc_unicode)
        self.assertEquals(json.dumps(doc2, ensure_ascii=False), doc_unicode)
