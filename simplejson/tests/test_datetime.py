import datetime
from datetime import datetime as DateTime, date as Date, time as Time
from unittest import TestCase
from simplejson.compat import StringIO, reload_module

import simplejson as json

class AbstractDatetimeTestSuite(object):
    VALUES = ()

    def dumps(self, obj, **kw):
        sio = StringIO()
        json.dump(obj, sio, **kw)
        res = json.dumps(obj, **kw)
        self.assertEqual(res, sio.getvalue())
        return res

    def loads(self, s, **kw):
        sio = StringIO(s)
        res = json.loads(s, **kw)
        self.assertEqual(res, json.load(sio, **kw))
        return res

    def test_encode(self):
        for d in self.VALUES:
            self.assertEqual(self.dumps(d, iso_datetime=True), '"%sZ"' % d.isoformat())

    def test_decode(self):
        for d in self.VALUES:
            self.assertEqual(self.loads('"%s"' % d.isoformat(), iso_datetime=True), d)
            self.assertEqual(self.loads('"%sZ"' % d.isoformat(), iso_datetime=True), d)

    def test_stringify_key(self):
        for d in self.VALUES:
            v = {d: d}
            self.assertEqual(
                self.loads(
                    self.dumps(v, iso_datetime=True), iso_datetime=True),
                v)

    def test_roundtrip(self):
        for d in self.VALUES:
            for v in [d, [d], {'': d}]:
                self.assertEqual(
                    self.loads(
                        self.dumps(v, iso_datetime=True), iso_datetime=True),
                    v)

    def test_defaults(self):
        d = self.VALUES[0]
        self.assertRaises(TypeError, json.dumps, d)
        self.assertRaises(TypeError, json.dumps, d, iso_datetime=False)
        self.assertRaises(TypeError, json.dump, d, StringIO())
        self.assertRaises(TypeError, json.dump, d, StringIO(), iso_datetime=False)


class TestDatetime(TestCase, AbstractDatetimeTestSuite):
    VALUES = (DateTime(2014, 3, 18, 10, 10, 0),
              DateTime(1900, 1, 1, 0, 0, 0),
              DateTime(2014, 3, 18, 10, 10, 1, 1),
              DateTime(2014, 3, 18, 10, 10, 1, 100),
              DateTime(2014, 3, 18, 10, 10, 1, 10000),
              DateTime(2014, 3, 18, 10, 10, 1, 100000))

    def test_reload(self):
        # Simulate a subinterpreter that reloads the Python modules but not
        # the C code https://github.com/simplejson/simplejson/issues/34
        global DateTime
        DateTime = reload_module(datetime).datetime
        import simplejson.encoder
        simplejson.encoder.datetime = DateTime
        self.test_roundtrip()


class TestDate(TestCase, AbstractDatetimeTestSuite):
    VALUES = (Date(2014, 3, 18), Date(1900, 1, 1), Date(1, 1, 1))

    def test_encode(self):
        for d in self.VALUES:
            self.assertEqual(self.dumps(d, iso_datetime=True), '"%s"' % d.isoformat())

    def test_decode(self):
        for d in self.VALUES:
            self.assertEqual(self.loads('"%s"' % d.isoformat(), iso_datetime=True), d)

    def test_reload(self):
        # Simulate a subinterpreter that reloads the Python modules but not
        # the C code https://github.com/simplejson/simplejson/issues/34
        global Date
        Date = reload_module(datetime).date
        import simplejson.encoder
        simplejson.encoder.date = Date
        self.test_roundtrip()


class TestTime(TestCase, AbstractDatetimeTestSuite):
    VALUES = (Time(10, 10, 0), Time(0, 0, 0),
              Time(1, 1, 1, 1), Time(23,23,23,999999))


from datetime import tzinfo, timedelta

ZERO = timedelta(0)
HOUR = timedelta(hours=1)

# A UTC class.

class UTC(tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

utc = UTC()

class TestTimezoneAware(TestCase):
    def test(self):
        d = DateTime.now()
        d = d.replace(tzinfo=utc)
        self.assertRaises(TypeError, json.dumps, d, iso_datetime=True)
        t = d.time().replace(tzinfo=utc)
        self.assertRaises(TypeError, json.dumps, t, iso_datetime=True)
