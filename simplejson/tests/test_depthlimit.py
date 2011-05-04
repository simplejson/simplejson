from unittest import TestCase

import simplejson as json
from simplejson.scanner import JSON_TOKENER_MAX_DEPTH as MAX

OK = MAX - 1

class TestDepthLimit(TestCase):
    def _assertExceedsDepth(self, *args, **kwargs):
        try:
            json.loads(*args, **kwargs)
        except json.JSONDecodeError, exc:
            self.assertTrue(str(exc).startswith('Depth limit exceeded: line '))
        except Exception, exc:
            self.fail("json.loads raised %r instead of JSONDecodeError" % (exc,))
        else:
            self.fail("json.loads did not raise JSONDecodeError")

    def test_depthLimitStringArray(self):
        json.loads('[' * OK + '1' + ']' * OK)
        self._assertExceedsDepth('[' * MAX + '1' + ']' * MAX)

    def test_depthLimitUnicodeArray(self):
        json.loads(u'[' * OK + u'1' + u']' * OK)
        self._assertExceedsDepth(u'[' * MAX + u'1' + u']' * MAX)

    def test_depthLimitStringObject(self):
        json.loads('{"":' * OK + '1' + '}' * OK)
        self._assertExceedsDepth('{"":' * MAX + '1' + '}' * MAX)
        self._assertExceedsDepth('{"":' * OK + '[1]' + '}' * OK)

    def test_depthLimitUnicodeObject(self):
        json.loads(u'{"":' * OK + u'1' + u'}' * OK)
        self._assertExceedsDepth(u'{"":' * MAX + u'1' + u'}' * MAX)
        self._assertExceedsDepth(u'{"":' * OK + u'[1]' + u'}' * OK)
