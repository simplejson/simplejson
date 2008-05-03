from unittest import TestCase

import simplejson as S

class TestUnicode(TestCase):
    def test_encoding1(self):
        encoder = S.JSONEncoder(encoding='utf-8')
        u = u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}'
        s = u.encode('utf-8')
        ju = encoder.encode(u)
        js = encoder.encode(s)
        self.assertEquals(ju, js)
    
    def test_encoding2(self):
        u = u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}'
        s = u.encode('utf-8')
        ju = S.dumps(u, encoding='utf-8')
        js = S.dumps(s, encoding='utf-8')
        self.assertEquals(ju, js)

    def test_big_unicode_encode(self):
        u = u'\U0001d120'
        self.assertEquals(S.dumps(u), '"\\ud834\\udd20"')
        self.assertEquals(S.dumps(u, ensure_ascii=False), '"\\ud834\\udd20"')

    def test_big_unicode_decode(self):
        u = u'z\U0001d120x'
        self.assertEquals(S.loads('"' + u + '"'), u)
        self.assertEquals(S.loads('"z\\ud834\\udd20x"'), u)

    def test_unicode_decode(self):
        for i in range(0, 0xd7ff):
            u = unichr(i)
            json = '"\\u%04x"' % (i,)
            self.assertEquals(S.loads(json), u)