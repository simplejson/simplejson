# coding=UTF-8

from __future__ import absolute_import
from unittest import TestCase

import simplejson as json


class ReadChunkedFile(object):
    '''A file whose reads come in predefined chunks.'''
    def __init__(self, *pieces):
        self.pieces = iter(pieces)

    def read(self):
        try:
            return next(self.pieces)
        except StopIteration:
            return ''


class TestMultibyte(TestCase):
    if not hasattr(TestCase, 'assertIs'):
        def assertIs(self, a, b):
            self.assertTrue(a is b, '%r is %r' % (a, b))

    def test_load_with_split_unicode(self):
        # These together produce JSON-encoded 'ü'
        first, second = '"\\u00', 'fc"'
        self.assertEqual(u'ü', json.loads(first + second))

        # This is the content split over two successive reads
        fin = ReadChunkedFile(first, second)
        self.assertEqual(u'ü', json.load(fin))

    def test_load_with_split_utf8(self):
        # These together produce JSON-encoded 'ü'
        first, second = '"\xC3', '\xBC"'
        self.assertEqual(u'ü', json.loads(first + second))

        # This is the content split over two successive reads
        fin = ReadChunkedFile(first, second)
        self.assertEqual(u'ü', json.load(fin))
