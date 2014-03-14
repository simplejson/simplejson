"""Implementation of JSONDecoder
"""
from __future__ import absolute_import
import re
import sys
import struct
from .compat import fromhex, b, u, text_type, binary_type, PY3, unichr
from .scanner import make_scanner, JSONDecodeError

def _import_c_scanstring():
    try:
        from ._speedups import scanstring
        return scanstring
    except ImportError:
        return None
c_scanstring = _import_c_scanstring()

# NOTE (3.1.0): JSONDecodeError may still be imported from this module for
# compatibility, but it was never in the __all__
__all__ = ['JSONDecoder']

FLAGS = re.VERBOSE | re.MULTILINE | re.DOTALL

def _floatconstants():
    _BYTES = fromhex('7FF80000000000007FF0000000000000')
    # The struct module in Python 2.4 would get frexp() out of range here
    # when an endian is specified in the format string. Fixed in Python 2.5+
    if sys.byteorder != 'big':
        _BYTES = _BYTES[:8][::-1] + _BYTES[8:][::-1]
    nan, inf = struct.unpack('dd', _BYTES)
    return nan, inf, -inf

NaN, PosInf, NegInf = _floatconstants()

_CONSTANTS = {
    '-Infinity': NegInf,
    'Infinity': PosInf,
    'NaN': NaN,
}

STRINGCHUNK = re.compile(r'(.*?)(["\\\x00-\x1f])', FLAGS)
BACKSLASH = {
    '"': u('"'), '\\': u('\u005c'), '/': u('/'),
    'b': u('\b'), 'f': u('\f'), 'n': u('\n'), 'r': u('\r'), 't': u('\t'),
}

DEFAULT_ENCODING = "utf-8"

def _datetime_or_string(string):
    from datetime import date, datetime, time

    l = len(string)

    # Maybe a date
    if l == 10:
        chunks = string.split('-')
        if len(chunks) == 3:
            try:
                y, m, d = map(int, chunks)
            except ValueError:
                pass
            else:
                return date(y, m, d)

    # Maybe a datetime
    if l == 19 or l == 20 or l == 23 or l == 24 or l == 26 or l == 27:
        if 'T' in string:
            pieces = string.split('T')
        else:
            pieces = string.split(' ')
        if len(pieces) == 2:
            chunks = pieces[0].split('-')
            if len(chunks) == 3:
                chunks.extend(pieces[1].split(':'))
                if len(chunks) == 6:
                    if chunks[-1].endswith('Z'):
                        chunks[-1] = chunks[-1][:-1]
                    if '.' in chunks[-1]:
                        chunks[-1:] = chunks[-1].split('.')
                    else:
                        chunks.append('0')
                    if len(chunks) == 7:
                        if len(chunks[-1]) == 3:
                            chunks[-1] += '000'
                        try:
                            y, mo, d, h, m, s, ms = map(int, chunks)
                        except ValueError:
                            pass
                        else:
                            return datetime(y, mo, d, h, m, s, ms)

    # Maybe a time
    if l == 8 or l == 9 or l == 12 or l == 13 or l == 15 or l == 16:
        chunks = string.split(':')
        if len(chunks) == 3:
            if chunks[-1].endswith('Z'):
                chunks[-1] = chunks[-1][:-1]
            if '.' in chunks[-1]:
                chunks[-1:] = chunks[-1].split('.')
            else:
                chunks.append('0')
            if len(chunks) == 4:
                if len(chunks[-1]) == 3:
                    chunks[-1] += '000'
                try:
                    h, m, s, ms = map(int, chunks)
                except ValueError:
                    pass
                else:
                    return time(h, m, s, ms)

    return string

def py_scanstring(s, end, encoding=None, strict=True, handle_datetime=False,
        _b=BACKSLASH, _m=STRINGCHUNK.match, _join=u('').join,
        _PY3=PY3, _maxunicode=sys.maxunicode):
    """Scan the string s for a JSON string. End is the index of the
    character in s after the quote that started the JSON string.
    Unescapes all valid JSON string escape sequences and raises ValueError
    on attempt to decode an invalid string. If strict is False then literal
    control characters are allowed in the string.

    Returns a tuple of the decoded string and the index of the character in s
    after the end quote."""
    if encoding is None:
        encoding = DEFAULT_ENCODING
    chunks = []
    _append = chunks.append
    begin = end - 1
    while 1:
        chunk = _m(s, end)
        if chunk is None:
            raise JSONDecodeError(
                "Unterminated string starting at", s, begin)
        end = chunk.end()
        content, terminator = chunk.groups()
        # Content is contains zero or more unescaped string characters
        if content:
            if not _PY3 and not isinstance(content, text_type):
                content = text_type(content, encoding)
            _append(content)
        # Terminator is the end of string, a literal control character,
        # or a backslash denoting that an escape sequence follows
        if terminator == '"':
            break
        elif terminator != '\\':
            if strict:
                msg = "Invalid control character %r at"
                raise JSONDecodeError(msg, s, end)
            else:
                _append(terminator)
                continue
        try:
            esc = s[end]
        except IndexError:
            raise JSONDecodeError(
                "Unterminated string starting at", s, begin)
        # If not a unicode escape sequence, must be in the lookup table
        if esc != 'u':
            try:
                char = _b[esc]
            except KeyError:
                msg = "Invalid \\X escape sequence %r"
                raise JSONDecodeError(msg, s, end)
            end += 1
        else:
            # Unicode escape sequence
            msg = "Invalid \\uXXXX escape sequence"
            esc = s[end + 1:end + 5]
            escX = esc[1:2]
            if len(esc) != 4 or escX == 'x' or escX == 'X':
                raise JSONDecodeError(msg, s, end - 1)
            try:
                uni = int(esc, 16)
            except ValueError:
                raise JSONDecodeError(msg, s, end - 1)
            end += 5
            # Check for surrogate pair on UCS-4 systems
            # Note that this will join high/low surrogate pairs
            # but will also pass unpaired surrogates through
            if (_maxunicode > 65535 and
                uni & 0xfc00 == 0xd800 and
                s[end:end + 2] == '\\u'):
                esc2 = s[end + 2:end + 6]
                escX = esc2[1:2]
                if len(esc2) == 4 and not (escX == 'x' or escX == 'X'):
                    try:
                        uni2 = int(esc2, 16)
                    except ValueError:
                        raise JSONDecodeError(msg, s, end)
                    if uni2 & 0xfc00 == 0xdc00:
                        uni = 0x10000 + (((uni - 0xd800) << 10) |
                                         (uni2 - 0xdc00))
                        end += 6
            char = unichr(uni)
        # Append the unescaped character
        _append(char)

    s = _join(chunks)
    if handle_datetime:
        s = _datetime_or_string(s)
    return s, end


# Use speedup if available
scanstring = c_scanstring or py_scanstring

WHITESPACE = re.compile(r'[ \t\n\r]*', FLAGS)
WHITESPACE_STR = ' \t\n\r'

def JSONObject(state, encoding, strict, scan_once, object_hook,
        object_pairs_hook, handle_datetime, memo=None,
        _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    (s, end) = state
    # Backwards compatibility
    if memo is None:
        memo = {}
    memo_get = memo.setdefault
    pairs = []
    # Use a slice to prevent IndexError from being raised, the following
    # check will raise a more specific ValueError if the string is empty
    nextchar = s[end:end + 1]
    # Normally we expect nextchar == '"'
    if nextchar != '"':
        if nextchar in _ws:
            end = _w(s, end).end()
            nextchar = s[end:end + 1]
        # Trivial empty object
        if nextchar == '}':
            if object_pairs_hook is not None:
                result = object_pairs_hook(pairs)
                return result, end + 1
            pairs = {}
            if object_hook is not None:
                pairs = object_hook(pairs)
            return pairs, end + 1
        elif nextchar != '"':
            raise JSONDecodeError(
                "Expecting property name enclosed in double quotes",
                s, end)
    end += 1
    while True:
        key, end = scanstring(s, end, encoding, strict, handle_datetime)
        key = memo_get(key, key)

        # To skip some function call overhead we optimize the fast paths where
        # the JSON key separator is ": " or just ":".
        if s[end:end + 1] != ':':
            end = _w(s, end).end()
            if s[end:end + 1] != ':':
                raise JSONDecodeError("Expecting ':' delimiter", s, end)

        end += 1

        try:
            if s[end] in _ws:
                end += 1
                if s[end] in _ws:
                    end = _w(s, end + 1).end()
        except IndexError:
            pass

        value, end = scan_once(s, end)
        pairs.append((key, value))

        try:
            nextchar = s[end]
            if nextchar in _ws:
                end = _w(s, end + 1).end()
                nextchar = s[end]
        except IndexError:
            nextchar = ''
        end += 1

        if nextchar == '}':
            break
        elif nextchar != ',':
            raise JSONDecodeError("Expecting ',' delimiter or '}'", s, end - 1)

        try:
            nextchar = s[end]
            if nextchar in _ws:
                end += 1
                nextchar = s[end]
                if nextchar in _ws:
                    end = _w(s, end + 1).end()
                    nextchar = s[end]
        except IndexError:
            nextchar = ''

        end += 1
        if nextchar != '"':
            raise JSONDecodeError(
                "Expecting property name enclosed in double quotes",
                s, end - 1)

    if object_pairs_hook is not None:
        result = object_pairs_hook(pairs)
        return result, end
    pairs = dict(pairs)
    if object_hook is not None:
        pairs = object_hook(pairs)
    return pairs, end

def JSONArray(state, scan_once, _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    (s, end) = state
    values = []
    nextchar = s[end:end + 1]
    if nextchar in _ws:
        end = _w(s, end + 1).end()
        nextchar = s[end:end + 1]
    # Look-ahead for trivial empty array
    if nextchar == ']':
        return values, end + 1
    elif nextchar == '':
        raise JSONDecodeError("Expecting value or ']'", s, end)
    _append = values.append
    while True:
        value, end = scan_once(s, end)
        _append(value)
        nextchar = s[end:end + 1]
        if nextchar in _ws:
            end = _w(s, end + 1).end()
            nextchar = s[end:end + 1]
        end += 1
        if nextchar == ']':
            break
        elif nextchar != ',':
            raise JSONDecodeError("Expecting ',' delimiter or ']'", s, end - 1)

        try:
            if s[end] in _ws:
                end += 1
                if s[end] in _ws:
                    end = _w(s, end + 1).end()
        except IndexError:
            pass

    return values, end

class JSONDecoder(object):
    """Simple JSON <http://json.org> decoder

    Performs the following translations in decoding by default:

    +---------------+-------------------+
    | JSON          | Python            |
    +===============+===================+
    | object        | dict              |
    +---------------+-------------------+
    | array         | list              |
    +---------------+-------------------+
    | string        | str, unicode      |
    +---------------+-------------------+
    | number (int)  | int, long         |
    +---------------+-------------------+
    | number (real) | float             |
    +---------------+-------------------+
    | true          | True              |
    +---------------+-------------------+
    | false         | False             |
    +---------------+-------------------+
    | null          | None              |
    +---------------+-------------------+

    It also understands ``NaN``, ``Infinity``, and ``-Infinity`` as
    their corresponding ``float`` values, which is outside the JSON spec.

    """

    def __init__(self, encoding=None, object_hook=None, parse_float=None,
            parse_int=None, parse_constant=None, strict=True,
            object_pairs_hook=None, handle_datetime=False):
        """
        *encoding* determines the encoding used to interpret any
        :class:`str` objects decoded by this instance (``'utf-8'`` by
        default).  It has no effect when decoding :class:`unicode` objects.

        Note that currently only encodings that are a superset of ASCII work,
        strings of other encodings should be passed in as :class:`unicode`.

        *object_hook*, if specified, will be called with the result of every
        JSON object decoded and its return value will be used in place of the
        given :class:`dict`.  This can be used to provide custom
        deserializations (e.g. to support JSON-RPC class hinting).

        *object_pairs_hook* is an optional function that will be called with
        the result of any object literal decode with an ordered list of pairs.
        The return value of *object_pairs_hook* will be used instead of the
        :class:`dict`.  This feature can be used to implement custom decoders
        that rely on the order that the key and value pairs are decoded (for
        example, :func:`collections.OrderedDict` will remember the order of
        insertion). If *object_hook* is also defined, the *object_pairs_hook*
        takes priority.

        *parse_float*, if specified, will be called with the string of every
        JSON float to be decoded.  By default, this is equivalent to
        ``float(num_str)``. This can be used to use another datatype or parser
        for JSON floats (e.g. :class:`decimal.Decimal`).

        *parse_int*, if specified, will be called with the string of every
        JSON int to be decoded.  By default, this is equivalent to
        ``int(num_str)``.  This can be used to use another datatype or parser
        for JSON integers (e.g. :class:`float`).

        *parse_constant*, if specified, will be called with one of the
        following strings: ``'-Infinity'``, ``'Infinity'``, ``'NaN'``.  This
        can be used to raise an exception if invalid JSON numbers are
        encountered.

        *handle_datetime*, if true (by default it's false), means that the parse
        will recognize ISO formatted date and datetimes and will return
        :class:`datetime.date` and :class:`datetime.datetime` respectively.

        *strict* controls the parser's behavior when it encounters an
        invalid control character in a string. The default setting of
        ``True`` means that unescaped control characters are parse errors, if
        ``False`` then control characters will be allowed in strings.

        """
        if encoding is None:
            encoding = DEFAULT_ENCODING
        self.encoding = encoding
        self.object_hook = object_hook
        self.object_pairs_hook = object_pairs_hook
        self.parse_float = parse_float or float
        self.parse_int = parse_int or int
        self.parse_constant = parse_constant or _CONSTANTS.__getitem__
        self.strict = strict
        self.parse_object = JSONObject
        self.parse_array = JSONArray
        self.parse_string = scanstring
        self.handle_datetime = handle_datetime
        self.memo = {}
        self.scan_once = make_scanner(self)

    def decode(self, s, _w=WHITESPACE.match, _PY3=PY3):
        """Return the Python representation of ``s`` (a ``str`` or ``unicode``
        instance containing a JSON document)

        """
        if _PY3 and isinstance(s, binary_type):
            s = s.decode(self.encoding)
        obj, end = self.raw_decode(s)
        end = _w(s, end).end()
        if end != len(s):
            raise JSONDecodeError("Extra data", s, end, len(s))
        return obj

    def raw_decode(self, s, idx=0, _w=WHITESPACE.match, _PY3=PY3):
        """Decode a JSON document from ``s`` (a ``str`` or ``unicode``
        beginning with a JSON document) and return a 2-tuple of the Python
        representation and the index in ``s`` where the document ended.
        Optionally, ``idx`` can be used to specify an offset in ``s`` where
        the JSON document begins.

        This can be used to decode a JSON document from a string that may
        have extraneous data at the end.

        """
        if _PY3 and not isinstance(s, text_type):
            raise TypeError("Input string must be text, not bytes")
        return self.scan_once(s, idx=_w(s, idx).end())
