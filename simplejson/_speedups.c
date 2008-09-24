#include "Python.h"
#include "structmember.h"
#if PY_VERSION_HEX < 0x02060000 && !defined(Py_TYPE)
#define Py_TYPE(ob)     (((PyObject*)(ob))->ob_type)
#endif
#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#define PyInt_FromSsize_t PyInt_FromLong
#define PyInt_AsSsize_t PyInt_AsLong
#endif

#ifdef __GNUC__
#define UNUSED __attribute__((__unused__))
#else
#define UNUSED
#endif

#define DEFAULT_ENCODING "utf-8"

#define PyScanner_Check(op) PyObject_TypeCheck(op, &PyScannerType)
#define PyScanner_CheckExact(op) (Py_TYPE(op) == &PyScannerType)

static PyTypeObject PyScannerType;

typedef struct _PyScannerObject {
    PyObject_HEAD
    PyObject *encoding;
    PyObject *strict;
    PyObject *object_hook;
    PyObject *parse_float;
    PyObject *parse_int;
    PyObject *parse_constant;
} PyScannerObject;

static PyMemberDef scanner_members[] = {
    {"encoding", T_OBJECT, offsetof(PyScannerObject, encoding), READONLY, "encoding"},
    {"strict", T_OBJECT, offsetof(PyScannerObject, strict), READONLY, "strict"},
    {"object_hook", T_OBJECT, offsetof(PyScannerObject, object_hook), READONLY, "object_hook"},
    {"parse_float", T_OBJECT, offsetof(PyScannerObject, parse_float), READONLY, "parse_float"},
    {"parse_int", T_OBJECT, offsetof(PyScannerObject, parse_int), READONLY, "parse_int"},
    {"parse_constant", T_OBJECT, offsetof(PyScannerObject, parse_constant), READONLY, "parse_constant"},
    {NULL}
};

static Py_ssize_t
ascii_escape_char(Py_UNICODE c, char *output, Py_ssize_t chars);
static PyObject *
ascii_escape_unicode(PyObject *pystr);
static PyObject *
ascii_escape_str(PyObject *pystr);
static PyObject *
py_encode_basestring_ascii(PyObject* self UNUSED, PyObject *pystr);
void init_speedups(void);
static PyObject *
scan_once_str(PyScannerObject *s, PyObject *pystr, Py_ssize_t idx);
static PyObject *
scan_once_unicode(PyScannerObject *s, PyObject *pystr, Py_ssize_t idx);

    
#define S_CHAR(c) (c >= ' ' && c <= '~' && c != '\\' && c != '"')

#define MIN_EXPANSION 6
#ifdef Py_UNICODE_WIDE
#define MAX_EXPANSION (2 * MIN_EXPANSION)
#else
#define MAX_EXPANSION MIN_EXPANSION
#endif


static Py_ssize_t
ascii_escape_char(Py_UNICODE c, char *output, Py_ssize_t chars)
{
    Py_UNICODE x;
    output[chars++] = '\\';
    switch (c) {
        case '\\': output[chars++] = (char)c; break;
        case '"': output[chars++] = (char)c; break;
        case '\b': output[chars++] = 'b'; break;
        case '\f': output[chars++] = 'f'; break;
        case '\n': output[chars++] = 'n'; break;
        case '\r': output[chars++] = 'r'; break;
        case '\t': output[chars++] = 't'; break;
        default:
#ifdef Py_UNICODE_WIDE
            if (c >= 0x10000) {
                /* UTF-16 surrogate pair */
                Py_UNICODE v = c - 0x10000;
                c = 0xd800 | ((v >> 10) & 0x3ff);
                output[chars++] = 'u';
                x = (c & 0xf000) >> 12;
                output[chars++] = (x < 10) ? '0' + x : 'a' + (x - 10);
                x = (c & 0x0f00) >> 8;
                output[chars++] = (x < 10) ? '0' + x : 'a' + (x - 10);
                x = (c & 0x00f0) >> 4;
                output[chars++] = (x < 10) ? '0' + x : 'a' + (x - 10);
                x = (c & 0x000f);
                output[chars++] = (x < 10) ? '0' + x : 'a' + (x - 10);
                c = 0xdc00 | (v & 0x3ff);
                output[chars++] = '\\';
            }
#endif
            output[chars++] = 'u';
            x = (c & 0xf000) >> 12;
            output[chars++] = (x < 10) ? '0' + x : 'a' + (x - 10);
            x = (c & 0x0f00) >> 8;
            output[chars++] = (x < 10) ? '0' + x : 'a' + (x - 10);
            x = (c & 0x00f0) >> 4;
            output[chars++] = (x < 10) ? '0' + x : 'a' + (x - 10);
            x = (c & 0x000f);
            output[chars++] = (x < 10) ? '0' + x : 'a' + (x - 10);
    }
    return chars;
}

static PyObject *
ascii_escape_unicode(PyObject *pystr)
{
    Py_ssize_t i;
    Py_ssize_t input_chars;
    Py_ssize_t output_size;
    Py_ssize_t chars;
    PyObject *rval;
    char *output;
    Py_UNICODE *input_unicode;

    input_chars = PyUnicode_GET_SIZE(pystr);
    input_unicode = PyUnicode_AS_UNICODE(pystr);
    /* One char input can be up to 6 chars output, estimate 4 of these */
    output_size = 2 + (MIN_EXPANSION * 4) + input_chars;
    rval = PyString_FromStringAndSize(NULL, output_size);
    if (rval == NULL) {
        return NULL;
    }
    output = PyString_AS_STRING(rval);
    chars = 0;
    output[chars++] = '"';
    for (i = 0; i < input_chars; i++) {
        Py_UNICODE c = input_unicode[i];
        if (S_CHAR(c)) {
            output[chars++] = (char)c;
        }
        else {
            chars = ascii_escape_char(c, output, chars);
        }
        if (output_size - chars < (1 + MAX_EXPANSION)) {
            /* There's more than four, so let's resize by a lot */
            output_size *= 2;
            /* This is an upper bound */
            if (output_size > 2 + (input_chars * MAX_EXPANSION)) {
                output_size = 2 + (input_chars * MAX_EXPANSION);
            }
            if (_PyString_Resize(&rval, output_size) == -1) {
                return NULL;
            }
            output = PyString_AS_STRING(rval);
        }
    }
    output[chars++] = '"';
    if (_PyString_Resize(&rval, chars) == -1) {
        return NULL;
    }
    return rval;
}

static PyObject *
ascii_escape_str(PyObject *pystr)
{
    Py_ssize_t i;
    Py_ssize_t input_chars;
    Py_ssize_t output_size;
    Py_ssize_t chars;
    PyObject *rval;
    char *output;
    char *input_str;

    input_chars = PyString_GET_SIZE(pystr);
    input_str = PyString_AS_STRING(pystr);
    /* One char input can be up to 6 chars output, estimate 4 of these */
    output_size = 2 + (MIN_EXPANSION * 4) + input_chars;
    rval = PyString_FromStringAndSize(NULL, output_size);
    if (rval == NULL) {
        return NULL;
    }
    output = PyString_AS_STRING(rval);
    chars = 0;
    output[chars++] = '"';
    for (i = 0; i < input_chars; i++) {
        Py_UNICODE c = (Py_UNICODE)input_str[i];
        if (S_CHAR(c)) {
            output[chars++] = (char)c;
        }
        else if (c > 0x7F) {
            /* We hit a non-ASCII character, bail to unicode mode */
            PyObject *uni;
            Py_DECREF(rval);
            uni = PyUnicode_DecodeUTF8(input_str, input_chars, "strict");
            if (uni == NULL) {
                return NULL;
            }
            rval = ascii_escape_unicode(uni);
            Py_DECREF(uni);
            return rval;
        }
        else {
            chars = ascii_escape_char(c, output, chars);
        }
        /* An ASCII char can't possibly expand to a surrogate! */
        if (output_size - chars < (1 + MIN_EXPANSION)) {
            /* There's more than four, so let's resize by a lot */
            output_size *= 2;
            if (output_size > 2 + (input_chars * MIN_EXPANSION)) {
                output_size = 2 + (input_chars * MIN_EXPANSION);
            }
            if (_PyString_Resize(&rval, output_size) == -1) {
                return NULL;
            }
            output = PyString_AS_STRING(rval);
        }
    }
    output[chars++] = '"';
    if (_PyString_Resize(&rval, chars) == -1) {
        return NULL;
    }
    return rval;
}

void
raise_errmsg(char *msg, PyObject *s, Py_ssize_t end)
{
    static PyObject *errmsg_fn = NULL;
    PyObject *pymsg;
    if (errmsg_fn == NULL) {
        PyObject *decoder = PyImport_ImportModule("simplejson.decoder");
        if (decoder == NULL) return;
        errmsg_fn = PyObject_GetAttrString(decoder, "errmsg");
        if (errmsg_fn == NULL) return;
        Py_XDECREF(decoder);
    }
#if PY_VERSION_HEX < 0x02050000 
    pymsg = PyObject_CallFunction(errmsg_fn, "(zOi)", msg, s, end);
#else
    pymsg = PyObject_CallFunction(errmsg_fn, "(zOn)", msg, s, end);
#endif
    PyErr_SetObject(PyExc_ValueError, pymsg);
    Py_DECREF(pymsg);
/*

def linecol(doc, pos):
    lineno = doc.count('\n', 0, pos) + 1
    if lineno == 1:
        colno = pos
    else:
        colno = pos - doc.rindex('\n', 0, pos)
    return lineno, colno

def errmsg(msg, doc, pos, end=None):
    lineno, colno = linecol(doc, pos)
    if end is None:
        return '%s: line %d column %d (char %d)' % (msg, lineno, colno, pos)
    endlineno, endcolno = linecol(doc, end)
    return '%s: line %d column %d - line %d column %d (char %d - %d)' % (
        msg, lineno, colno, endlineno, endcolno, pos, end)

*/
}

static PyObject *
join_list_unicode(PyObject *lst)
{
    static PyObject *ustr = NULL;
    static PyObject *joinstr = NULL;
    if (ustr == NULL) {
        Py_UNICODE c = 0;
        ustr = PyUnicode_FromUnicode(&c, 0);
    }
    if (joinstr == NULL) {
        joinstr = PyString_InternFromString("join");
    }
    if (joinstr == NULL || ustr == NULL) {
        return NULL;
    }
    return PyObject_CallMethodObjArgs(ustr, joinstr, lst, NULL);
}

static PyObject *
scanstring_str(PyObject *pystr, Py_ssize_t end, char *encoding, int strict)
{
    PyObject *rval;
    Py_ssize_t len = PyString_GET_SIZE(pystr);
    Py_ssize_t begin = end - 1;
    Py_ssize_t next = begin;
    char *buf = PyString_AS_STRING(pystr);
    PyObject *chunks = PyList_New(0);
    if (chunks == NULL) {
        goto bail;
    }
    if (end < 0 || len <= end) {
        PyErr_SetString(PyExc_ValueError, "end is out of bounds");
        goto bail;
    }
    while (1) {
        /* Find the end of the string or the next escape */
        Py_UNICODE c = 0;
        PyObject *chunk = NULL;
        for (next = end; next < len; next++) {
            c = buf[next];
            if (c == '"' || c == '\\') {
                break;
            }
            else if (strict && c <= 0x1f) {
                raise_errmsg("Invalid control character at", pystr, next);
                goto bail;
            }
        }
        if (!(c == '"' || c == '\\')) {
            raise_errmsg("Unterminated string starting at", pystr, begin);
            goto bail;
        }
        /* Pick up this chunk if it's not zero length */
        if (next != end) {
            PyObject *strchunk = PyBuffer_FromMemory(&buf[end], next - end);
            if (strchunk == NULL) {
                goto bail;
            }
            chunk = PyUnicode_FromEncodedObject(strchunk, encoding, NULL);
            Py_DECREF(strchunk);
            if (chunk == NULL) {
                goto bail;
            }
            if (PyList_Append(chunks, chunk)) {
                goto bail;
            }
            Py_DECREF(chunk);
        }
        next++;
        if (c == '"') {
            end = next;
            break;
        }
        if (next == len) {
            raise_errmsg("Unterminated string starting at", pystr, begin);
            goto bail;
        }
        c = buf[next];
        if (c != 'u') {
            /* Non-unicode backslash escapes */
            end = next + 1;
            switch (c) {
                case '"': break;
                case '\\': break;
                case '/': break;
                case 'b': c = '\b'; break;
                case 'f': c = '\f'; break;
                case 'n': c = '\n'; break;
                case 'r': c = '\r'; break;
                case 't': c = '\t'; break;
                default: c = 0;
            }
            if (c == 0) {
                raise_errmsg("Invalid \\escape", pystr, end - 2);
                goto bail;
            }
        }
        else {
            c = 0;
            next++;
            end = next + 4;
            if (end >= len) {
                raise_errmsg("Invalid \\uXXXX escape", pystr, next - 1);
                goto bail;
            }
            /* Decode 4 hex digits */
            for (; next < end; next++) {
                Py_ssize_t shl = (end - next - 1) << 2;
                Py_UNICODE digit = buf[next];
                switch (digit) {
                    case '0': case '1': case '2': case '3': case '4':
                    case '5': case '6': case '7': case '8': case '9':
                        c |= (digit - '0') << shl; break;
                    case 'a': case 'b': case 'c': case 'd': case 'e':
                    case 'f':
                        c |= (digit - 'a' + 10) << shl; break;
                    case 'A': case 'B': case 'C': case 'D': case 'E':
                    case 'F':
                        c |= (digit - 'A' + 10) << shl; break;
                    default:
                        raise_errmsg("Invalid \\uXXXX escape", pystr, end - 5);
                        goto bail;
                }
            }
#ifdef Py_UNICODE_WIDE
            /* Surrogate pair */
            if (c >= 0xd800 && c <= 0xdbff) {
                Py_UNICODE c2 = 0;
                if (end + 6 >= len) {
                    raise_errmsg("Invalid \\uXXXX\\uXXXX surrogate pair", pystr,
                        end - 5);
                }
                if (buf[next++] != '\\' || buf[next++] != 'u') {
                    raise_errmsg("Invalid \\uXXXX\\uXXXX surrogate pair", pystr,
                        end - 5);
                }
                end += 6;
                /* Decode 4 hex digits */
                for (; next < end; next++) {
                    Py_ssize_t shl = (end - next - 1) << 2;
                    Py_UNICODE digit = buf[next];
                    switch (digit) {
                        case '0': case '1': case '2': case '3': case '4':
                        case '5': case '6': case '7': case '8': case '9':
                            c2 |= (digit - '0') << shl; break;
                        case 'a': case 'b': case 'c': case 'd': case 'e':
                        case 'f':
                            c2 |= (digit - 'a' + 10) << shl; break;
                        case 'A': case 'B': case 'C': case 'D': case 'E':
                        case 'F':
                            c2 |= (digit - 'A' + 10) << shl; break;
                        default:
                            raise_errmsg("Invalid \\uXXXX escape", pystr, end - 5);
                            goto bail;
                    }
                }
                c = 0x10000 + (((c - 0xd800) << 10) | (c2 - 0xdc00));
            }
#endif
        }
        chunk = PyUnicode_FromUnicode(&c, 1);
        if (chunk == NULL) {
            goto bail;
        }
        if (PyList_Append(chunks, chunk)) {
            goto bail;
        }
        Py_DECREF(chunk);
    }

    rval = join_list_unicode(chunks);
    if (rval == NULL) {
        goto bail;
    }
    Py_DECREF(chunks);
    chunks = NULL;
#if PY_VERSION_HEX < 0x02050000 
    return Py_BuildValue("(Ni)", rval, end);
#else
    return Py_BuildValue("(Nn)", rval, end);
#endif
bail:
    Py_XDECREF(chunks);
    return NULL;
}


static PyObject *
scanstring_unicode(PyObject *pystr, Py_ssize_t end, int strict)
{
    PyObject *rval;
    Py_ssize_t len = PyUnicode_GET_SIZE(pystr);
    Py_ssize_t begin = end - 1;
    Py_ssize_t next = begin;
    const Py_UNICODE *buf = PyUnicode_AS_UNICODE(pystr);
    PyObject *chunks = PyList_New(0);
    if (chunks == NULL) {
        goto bail;
    }
    if (end < 0 || len <= end) {
        PyErr_SetString(PyExc_ValueError, "end is out of bounds");
        goto bail;
    }
    while (1) {
        /* Find the end of the string or the next escape */
        Py_UNICODE c = 0;
        PyObject *chunk = NULL;
        for (next = end; next < len; next++) {
            c = buf[next];
            if (c == '"' || c == '\\') {
                break;
            }
            else if (strict && c <= 0x1f) {
                raise_errmsg("Invalid control character at", pystr, next);
                goto bail;
            }
        }
        if (!(c == '"' || c == '\\')) {
            raise_errmsg("Unterminated string starting at", pystr, begin);
            goto bail;
        }
        /* Pick up this chunk if it's not zero length */
        if (next != end) {
            chunk = PyUnicode_FromUnicode(&buf[end], next - end);
            if (chunk == NULL) {
                goto bail;
            }
            if (PyList_Append(chunks, chunk)) {
                goto bail;
            }
            Py_DECREF(chunk);
        }
        next++;
        if (c == '"') {
            end = next;
            break;
        }
        if (next == len) {
            raise_errmsg("Unterminated string starting at", pystr, begin);
            goto bail;
        }
        c = buf[next];
        if (c != 'u') {
            /* Non-unicode backslash escapes */
            end = next + 1;
            switch (c) {
                case '"': break;
                case '\\': break;
                case '/': break;
                case 'b': c = '\b'; break;
                case 'f': c = '\f'; break;
                case 'n': c = '\n'; break;
                case 'r': c = '\r'; break;
                case 't': c = '\t'; break;
                default: c = 0;
            }
            if (c == 0) {
                raise_errmsg("Invalid \\escape", pystr, end - 2);
                goto bail;
            }
        }
        else {
            c = 0;
            next++;
            end = next + 4;
            if (end >= len) {
                raise_errmsg("Invalid \\uXXXX escape", pystr, next - 1);
                goto bail;
            }
            /* Decode 4 hex digits */
            for (; next < end; next++) {
                Py_ssize_t shl = (end - next - 1) << 2;
                Py_UNICODE digit = buf[next];
                switch (digit) {
                    case '0': case '1': case '2': case '3': case '4':
                    case '5': case '6': case '7': case '8': case '9':
                        c |= (digit - '0') << shl; break;
                    case 'a': case 'b': case 'c': case 'd': case 'e':
                    case 'f':
                        c |= (digit - 'a' + 10) << shl; break;
                    case 'A': case 'B': case 'C': case 'D': case 'E':
                    case 'F':
                        c |= (digit - 'A' + 10) << shl; break;
                    default:
                        raise_errmsg("Invalid \\uXXXX escape", pystr, end - 5);
                        goto bail;
                }
            }
#ifdef Py_UNICODE_WIDE
            /* Surrogate pair */
            if (c >= 0xd800 && c <= 0xdbff) {
                Py_UNICODE c2 = 0;
                if (end + 6 >= len) {
                    raise_errmsg("Invalid \\uXXXX\\uXXXX surrogate pair", pystr,
                        end - 5);
                }
                if (buf[next++] != '\\' || buf[next++] != 'u') {
                    raise_errmsg("Invalid \\uXXXX\\uXXXX surrogate pair", pystr,
                        end - 5);
                }
                end += 6;
                /* Decode 4 hex digits */
                for (; next < end; next++) {
                    Py_ssize_t shl = (end - next - 1) << 2;
                    Py_UNICODE digit = buf[next];
                    switch (digit) {
                        case '0': case '1': case '2': case '3': case '4':
                        case '5': case '6': case '7': case '8': case '9':
                            c2 |= (digit - '0') << shl; break;
                        case 'a': case 'b': case 'c': case 'd': case 'e':
                        case 'f':
                            c2 |= (digit - 'a' + 10) << shl; break;
                        case 'A': case 'B': case 'C': case 'D': case 'E':
                        case 'F':
                            c2 |= (digit - 'A' + 10) << shl; break;
                        default:
                            raise_errmsg("Invalid \\uXXXX escape", pystr, end - 5);
                            goto bail;
                    }
                }
                c = 0x10000 + (((c - 0xd800) << 10) | (c2 - 0xdc00));
            }
#endif
        }
        chunk = PyUnicode_FromUnicode(&c, 1);
        if (chunk == NULL) {
            goto bail;
        }
        if (PyList_Append(chunks, chunk)) {
            goto bail;
        }
        Py_DECREF(chunk);
    }

    rval = join_list_unicode(chunks);
    if (rval == NULL) {
        goto bail;
    }
    Py_DECREF(chunks);
    chunks = NULL;
#if PY_VERSION_HEX < 0x02050000 
    return Py_BuildValue("(Ni)", rval, end);
#else
    return Py_BuildValue("(Nn)", rval, end);
#endif
bail:
    Py_XDECREF(chunks);
    return NULL;
}

PyDoc_STRVAR(pydoc_scanstring,
    "scanstring(basestring, end, encoding) -> (str, end)\n"
    "\n"
    "..."
);

static PyObject *
py_scanstring(PyObject* self UNUSED, PyObject *args)
{
    PyObject *pystr;
    Py_ssize_t end;
    char *encoding = NULL;
    int strict = 0;
#if PY_VERSION_HEX < 0x02050000 
    if (!PyArg_ParseTuple(args, "Oi|zi:scanstring", &pystr, &end, &encoding, &strict)) {
#else
    if (!PyArg_ParseTuple(args, "On|zi:scanstring", &pystr, &end, &encoding, &strict)) {
#endif
        return NULL;
    }
    if (encoding == NULL) {
        encoding = DEFAULT_ENCODING;
    }
    if (PyString_Check(pystr)) {
        return scanstring_str(pystr, end, encoding, strict);
    }
    else if (PyUnicode_Check(pystr)) {
        return scanstring_unicode(pystr, end, strict);
    }
    PyErr_Format(PyExc_TypeError,
                 "first argument must be a string, not %.80s",
                 Py_TYPE(pystr)->tp_name);
    return NULL;
}

PyDoc_STRVAR(pydoc_encode_basestring_ascii,
    "encode_basestring_ascii(basestring) -> str\n"
    "\n"
    "..."
);

static PyObject *
py_encode_basestring_ascii(PyObject* self UNUSED, PyObject *pystr)
{
    /* METH_O */
    if (PyString_Check(pystr)) {
        return ascii_escape_str(pystr);
    }
    else if (PyUnicode_Check(pystr)) {
        return ascii_escape_unicode(pystr);
    } else {
        PyErr_Format(PyExc_TypeError,
                     "first argument must be a string, not %.80s",
                     Py_TYPE(pystr)->tp_name);
        return NULL;
    }
}

static void
scanner_dealloc(PyObject *self)
{
    assert(PyScanner_Check(self));
    PyScannerObject *s = (PyScannerObject *)self;
    Py_XDECREF(s->encoding);
    Py_XDECREF(s->strict);
    Py_XDECREF(s->object_hook);
    Py_XDECREF(s->parse_float);
    Py_XDECREF(s->parse_int);
    Py_XDECREF(s->parse_constant);
    s->encoding = NULL;
    s->strict = NULL;
    s->object_hook = NULL;
    s->parse_float = NULL;
    s->parse_int = NULL;
    s->parse_constant = NULL;
    self->ob_type->tp_free(self);
}

/*
static void
_dp(char *name, PyObject *o) {
    if (o == NULL) {
        printf("%s = NULL\n", name);
    } else {
        PyObject *r = PyObject_Repr(o);
        printf("%s = %s\n", name, PyString_AS_STRING(r));
        Py_DECREF(r);
    }
}
*/

#define IS_WHITESPACE(c) (((c) == ' ') || ((c) == '\t') || ((c) == '\n') || ((c) == '\r'))
static PyObject *
_parse_object_str(PyScannerObject *s, PyObject *pystr, Py_ssize_t idx) {
    char *str = PyString_AS_STRING(pystr);
    Py_ssize_t end_idx = PyString_GET_SIZE(pystr) - 1;
    PyObject *pyidx = NULL;
    PyObject *tpl= NULL;
    PyObject *rval = PyDict_New();
    PyObject *key = NULL;
    char *encoding = PyString_AS_STRING(s->encoding);
    int strict = PyObject_IsTrue(s->strict);
    Py_ssize_t next_idx;
    if (rval == NULL) return NULL;
    while (idx <= end_idx && IS_WHITESPACE(str[idx])) idx++;
    if (idx <= end_idx && str[idx] != '}') {
        while (idx <= end_idx) {
            if (str[idx] != '"') {
                raise_errmsg("Expecting property name", pystr, idx);
                goto bail;
            }
            tpl = scanstring_str(pystr, idx + 1, encoding, strict);
            if (tpl == NULL) goto bail;
            next_idx = PyInt_AsSsize_t(PyTuple_GET_ITEM(tpl, 1));
            if (next_idx == -1 && PyErr_Occurred()) goto bail;
            key = PyTuple_GET_ITEM(tpl, 0);
            if (key == NULL) goto bail;
            Py_INCREF(key);
            Py_DECREF(tpl);
            idx = next_idx;
            tpl = NULL;
            while (idx <= end_idx && IS_WHITESPACE(str[idx])) idx++;
            if (idx > end_idx || str[idx] != ':') {
                raise_errmsg("Expecting : delimiter", pystr, idx);
                goto bail;
            }
            idx++;
            while (idx <= end_idx && IS_WHITESPACE(str[idx])) idx++;
            
            tpl = scan_once_str(s, pystr, idx);
            if (tpl == NULL) goto bail;
            next_idx = PyInt_AsSsize_t(PyTuple_GET_ITEM(tpl, 1));
            if (next_idx == -1 && PyErr_Occurred()) goto bail;
            if (PyDict_SetItem(rval, key, PyTuple_GET_ITEM(tpl, 0)) == -1) goto bail;
            Py_DECREF(tpl);
            idx = next_idx;
            tpl = NULL;
            while (idx <= end_idx && IS_WHITESPACE(str[idx])) idx++;
            if (idx > end_idx) break;
            if (str[idx] == '}') {
                break;
            } else if (str[idx] != ',') {
                raise_errmsg("Expecting , delimiter", pystr, idx);
                goto bail;
            }
            idx++;
            while (idx <= end_idx && IS_WHITESPACE(str[idx])) idx++;
        }
    }
    if (idx > end_idx) {
        raise_errmsg("Expecting object", pystr, end_idx);
        goto bail;
    }
    if (s->object_hook != Py_None) {
        tpl = PyObject_CallFunctionObjArgs(s->object_hook, rval, NULL);
        if (tpl == NULL) goto bail;
        Py_DECREF(rval);
        rval = tpl;
        tpl = NULL;
    }
    pyidx = PyInt_FromSsize_t(idx + 1);
    if (pyidx == NULL) goto bail;
    tpl = PyTuple_Pack(2, rval, pyidx);
    Py_DECREF(pyidx);
    Py_DECREF(rval);
    return tpl;
bail:
    Py_XDECREF(key);
    Py_XDECREF(tpl);
    Py_DECREF(rval);
    return NULL;    
}

static PyObject *
_parse_object_unicode(PyScannerObject *s, PyObject *pystr, Py_ssize_t idx) {
    Py_UNICODE *str = PyUnicode_AS_UNICODE(pystr);
    Py_ssize_t end_idx = PyUnicode_GET_SIZE(pystr) - 1;
    PyObject *pyidx = NULL;
    PyObject *tpl= NULL;
    PyObject *rval = PyDict_New();
    PyObject *key = NULL;
    int strict = PyObject_IsTrue(s->strict);
    Py_ssize_t next_idx;
    if (rval == NULL) return NULL;
    while (idx <= end_idx && IS_WHITESPACE(str[idx])) idx++;
    if (idx <= end_idx && str[idx] != '}') {
        while (idx <= end_idx) {
            if (str[idx] != '"') {
                raise_errmsg("Expecting property name", pystr, idx);
                goto bail;
            }
            tpl = scanstring_unicode(pystr, idx + 1, strict);
            if (tpl == NULL) goto bail;
            next_idx = PyInt_AsSsize_t(PyTuple_GET_ITEM(tpl, 1));
            if (next_idx == -1 && PyErr_Occurred()) goto bail;
            key = PyTuple_GET_ITEM(tpl, 0);
            if (key == NULL) goto bail;
            Py_INCREF(key);
            Py_DECREF(tpl);
            idx = next_idx;
            tpl = NULL;
            while (idx <= end_idx && IS_WHITESPACE(str[idx])) idx++;
            if (idx > end_idx || str[idx] != ':') {
                raise_errmsg("Expecting : delimiter", pystr, idx);
                goto bail;
            }
            idx++;
            while (idx <= end_idx && IS_WHITESPACE(str[idx])) idx++;
            
            tpl = scan_once_unicode(s, pystr, idx);
            if (tpl == NULL) goto bail;
            next_idx = PyInt_AsSsize_t(PyTuple_GET_ITEM(tpl, 1));
            if (next_idx == -1 && PyErr_Occurred()) goto bail;
            if (PyDict_SetItem(rval, key, PyTuple_GET_ITEM(tpl, 0)) == -1) goto bail;
            Py_DECREF(tpl);
            idx = next_idx;
            tpl = NULL;
            while (idx <= end_idx && IS_WHITESPACE(str[idx])) idx++;
            if (idx > end_idx) break;
            if (str[idx] == '}') {
                break;
            } else if (str[idx] != ',') {
                raise_errmsg("Expecting , delimiter", pystr, idx);
                goto bail;
            }
            idx++;
            while (idx <= end_idx && IS_WHITESPACE(str[idx])) idx++;
        }
    }
    if (idx > end_idx) {
        raise_errmsg("Expecting object", pystr, end_idx);
        goto bail;
    }
    if (s->object_hook != Py_None) {
        tpl = PyObject_CallFunctionObjArgs(s->object_hook, rval, NULL);
        if (tpl == NULL) goto bail;
        Py_DECREF(rval);
        rval = tpl;
        tpl = NULL;
    }
    pyidx = PyInt_FromSsize_t(idx + 1);
    if (pyidx == NULL) goto bail;
    tpl = PyTuple_Pack(2, rval, pyidx);
    Py_DECREF(pyidx);
    Py_DECREF(rval);
    return tpl;
bail:
    Py_XDECREF(key);
    Py_XDECREF(tpl);
    Py_DECREF(rval);
    return NULL;
}

static PyObject *
_parse_array_str(PyScannerObject *s, PyObject *pystr, Py_ssize_t idx) {
    char *str = PyString_AS_STRING(pystr);
    Py_ssize_t end_idx = PyString_GET_SIZE(pystr) - 1;
    PyObject *pyidx = NULL;
    PyObject *tpl= NULL;
    PyObject *rval = PyList_New(0);
    Py_ssize_t next_idx;
    if (rval == NULL) return NULL;
    while (idx <= end_idx && IS_WHITESPACE(str[idx])) idx++;
    if (idx <= end_idx && str[idx] != ']') {
        while (idx <= end_idx) {
            tpl = scan_once_str(s, pystr, idx);
            if (tpl == NULL) goto bail;
            next_idx = PyInt_AsSsize_t(PyTuple_GET_ITEM(tpl, 1));
            if (next_idx == -1 && PyErr_Occurred()) goto bail;
            if (PyList_Append(rval, PyTuple_GET_ITEM(tpl, 0)) == -1) goto bail;
            Py_DECREF(tpl);
            idx = next_idx;
            tpl = NULL;
            while (idx <= end_idx && IS_WHITESPACE(str[idx])) idx++;
            if (idx > end_idx) break;
            if (str[idx] == ']') {
                break;
            } else if (str[idx] != ',') {
                raise_errmsg("Expecting , delimiter", pystr, idx);
                goto bail;
            }
            idx++;
            while (idx <= end_idx && IS_WHITESPACE(str[idx])) idx++;
        }
    }
    if (idx > end_idx) {
        raise_errmsg("Expecting object", pystr, end_idx);
        goto bail;
    }
    pyidx = PyInt_FromSsize_t(idx + 1);
    if (pyidx == NULL) goto bail;
    tpl = PyTuple_Pack(2, rval, pyidx);
    Py_DECREF(pyidx);
    Py_DECREF(rval);
    return tpl;
bail:
    Py_XDECREF(tpl);
    Py_DECREF(rval);
    return NULL;
}

static PyObject *
_parse_array_unicode(PyScannerObject *s, PyObject *pystr, Py_ssize_t idx) {
    Py_UNICODE *str = PyUnicode_AS_UNICODE(pystr);
    Py_ssize_t end_idx = PyUnicode_GET_SIZE(pystr) - 1;
    PyObject *pyidx = NULL;
    PyObject *tpl= NULL;
    PyObject *rval = PyList_New(0);
    Py_ssize_t next_idx;
    if (rval == NULL) return NULL;
    while (idx <= end_idx && IS_WHITESPACE(str[idx])) idx++;
    if (idx <= end_idx && str[idx] != ']') {
        while (idx <= end_idx) {
            tpl = scan_once_unicode(s, pystr, idx);
            if (tpl == NULL) goto bail;
            next_idx = PyInt_AsSsize_t(PyTuple_GET_ITEM(tpl, 1));
            if (next_idx == -1 && PyErr_Occurred()) goto bail;
            if (PyList_Append(rval, PyTuple_GET_ITEM(tpl, 0)) == -1) goto bail;
            Py_DECREF(tpl);
            idx = next_idx;
            tpl = NULL;
            while (idx <= end_idx && IS_WHITESPACE(str[idx])) idx++;
            if (idx > end_idx) break;
            if (str[idx] == ']') {
                break;
            } else if (str[idx] != ',') {
                raise_errmsg("Expecting , delimiter", pystr, idx);
                goto bail;
            }
            idx++;
            while (idx <= end_idx && IS_WHITESPACE(str[idx])) idx++;
        }
    }
    if (idx > end_idx) {
        raise_errmsg("Expecting object", pystr, end_idx);
        goto bail;
    }
    pyidx = PyInt_FromSsize_t(idx + 1);
    if (pyidx == NULL) goto bail;
    tpl = PyTuple_Pack(2, rval, pyidx);
    Py_DECREF(pyidx);
    Py_DECREF(rval);
    return tpl;
bail:
    Py_XDECREF(tpl);
    Py_DECREF(rval);
    return NULL;
}

static PyObject *
_parse_constant(PyScannerObject *s, char *constant, Py_ssize_t idx) {
    PyObject *cstr;
    PyObject *rval;
    PyObject *pyidx;
    PyObject *tpl;
    
    cstr = PyString_InternFromString(constant);
    if (cstr == NULL) return NULL;
    rval = PyObject_CallFunctionObjArgs(s->parse_constant, cstr, NULL);
    Py_DECREF(cstr);
    if (rval == NULL) return NULL;
    pyidx = PyInt_FromSsize_t(idx + PyString_GET_SIZE(cstr));
    if (pyidx == NULL) { Py_DECREF(rval); return NULL; }
    tpl = PyTuple_Pack(2, rval, pyidx);
    Py_DECREF(rval);
    Py_DECREF(pyidx);
    return tpl;
}

static PyObject *
_match_number_str(PyScannerObject *s, PyObject *pystr, Py_ssize_t start) {
    char *str = PyString_AS_STRING(pystr);
    Py_ssize_t end_idx = PyString_GET_SIZE(pystr) - 1;
    Py_ssize_t idx = start;
    int is_float = 0;
    PyObject *rval;
    PyObject *numstr;
    PyObject *tpl;
    PyObject *pyidx;
    if (str[idx] == '-') {
        idx++;
        if (idx > end_idx) {
            PyErr_SetNone(PyExc_StopIteration);
            return NULL;
        }
    }
    if (str[idx] >= '1' && str[idx] <= '9') {
        idx++;
        while (idx <= end_idx && str[idx] >= '0' && str[idx] <= '9') idx++;
    } else if (str[idx] == '0') {
        idx++;
    } else {
        PyErr_SetNone(PyExc_StopIteration);
        return NULL;
    }
    if (idx < end_idx && str[idx] == '.' && str[idx + 1] >= '0' && str[idx + 1] <= '9') {
        is_float = 1;
        idx += 2;
        while (idx < end_idx && str[idx] >= '0' && str[idx] <= '9') idx++;
    }
    if (idx < end_idx && (str[idx] == 'e' || str[idx] == 'E')) {
        Py_ssize_t e_start = idx;
        idx++;
        if (idx < end_idx && (str[idx] == '-' || str[idx] == '+')) idx++;
        while (idx <= end_idx && str[idx] >= '0' && str[idx] <= '9') idx++;
        if (str[idx - 1] >= '0' && str[idx - 1] <= '9') {
            is_float = 1;
        } else {
            idx = e_start;
        }
    }
    pyidx = PyInt_FromSsize_t(idx);
    if (pyidx == NULL) return NULL;
    numstr = PyString_FromStringAndSize(&str[start], idx - start);
    if (numstr == NULL) { Py_DECREF(pyidx); return NULL; }
    if (is_float) {
        if (s->parse_float != (PyObject *)&PyFloat_Type) {
            rval = PyObject_CallFunctionObjArgs(s->parse_float, numstr, NULL);
        } else {
            rval = PyFloat_FromString(numstr, NULL);
        }
    } else {
        if (s->parse_int != (PyObject *)&PyInt_Type) {
            rval = PyObject_CallFunctionObjArgs(s->parse_int, numstr, NULL);
        } else {
            rval = PyInt_FromString(PyString_AS_STRING(numstr), NULL, 10);
        }
    }
    Py_DECREF(numstr);
    if (rval == NULL) { Py_DECREF(pyidx); return NULL; }
    tpl = PyTuple_Pack(2, rval, pyidx);
    Py_DECREF(pyidx);
    Py_DECREF(rval);
    return tpl;
}

static PyObject *
_match_number_unicode(PyScannerObject *s, PyObject *pystr, Py_ssize_t start) {
    Py_UNICODE *str = PyUnicode_AS_UNICODE(pystr);
    Py_ssize_t end_idx = PyUnicode_GET_SIZE(pystr) - 1;
    Py_ssize_t idx = start;
    int is_float = 0;
    PyObject *rval;
    PyObject *numstr;
    PyObject *tpl;
    PyObject *pyidx;
    if (str[idx] == '-') {
        idx++;
        if (idx > end_idx) {
            PyErr_SetNone(PyExc_StopIteration);
            return NULL;
        }
    }
    if (str[idx] >= '1' && str[idx] <= '9') {
        idx++;
        while (idx <= end_idx && str[idx] >= '0' && str[idx] <= '9') idx++;
    } else if (str[idx] == '0') {
        idx++;
    } else {
        PyErr_SetNone(PyExc_StopIteration);
        return NULL;
    }
    if (idx < end_idx && str[idx] == '.' && str[idx + 1] >= '0' && str[idx + 1] <= '9') {
        is_float = 1;
        idx += 2;
        while (idx < end_idx && str[idx] >= '0' && str[idx] <= '9') idx++;
    }
    if (idx < end_idx && (str[idx] == 'e' || str[idx] == 'E')) {
        Py_ssize_t e_start = idx;
        idx++;
        if (idx < end_idx && (str[idx] == '-' || str[idx] == '+')) idx++;
        while (idx <= end_idx && str[idx] >= '0' && str[idx] <= '9') idx++;
        if (str[idx - 1] >= '0' && str[idx - 1] <= '9') {
            is_float = 1;
        } else {
            idx = e_start;
        }
    }
    pyidx = PyInt_FromSsize_t(idx);
    if (pyidx == NULL) return NULL;
    numstr = PyUnicode_FromUnicode(&str[start], idx - start);
    if (numstr == NULL) { Py_DECREF(pyidx); return NULL; }
    if (is_float) {
        if (s->parse_float != (PyObject *)&PyFloat_Type) {
            rval = PyObject_CallFunctionObjArgs(s->parse_float, numstr, NULL);
        } else {
            rval = PyFloat_FromString(numstr, NULL);
        }
    } else {
        rval = PyObject_CallFunctionObjArgs(s->parse_int, numstr, NULL);
    }
    Py_DECREF(numstr);
    if (rval == NULL) { Py_DECREF(pyidx); return NULL; }
    tpl = PyTuple_Pack(2, rval, pyidx);
    Py_DECREF(pyidx);
    Py_DECREF(rval);
    return tpl;
}

static PyObject *
scan_once_str(PyScannerObject *s, PyObject *pystr, Py_ssize_t idx)
{
    char *str = PyString_AS_STRING(pystr);
    Py_ssize_t length = PyString_GET_SIZE(pystr);
    PyObject *pyidx;
    if (idx >= length) {
        PyErr_SetNone(PyExc_StopIteration);
        return NULL;
    }
    switch (str[idx]) {
        case '"': 
            return scanstring_str(pystr, idx + 1,
                PyString_AS_STRING(s->encoding),
                PyObject_IsTrue(s->strict));
        case '{':
            return _parse_object_str(s, pystr, idx + 1);
        case '[':
            return _parse_array_str(s, pystr, idx + 1);
        case 'n':
            if ((idx + 3 < length) && str[idx + 1] == 'u' && str[idx + 2] == 'l' && str[idx + 3] == 'l') {
                pyidx = PyInt_FromSsize_t(idx + 4);
                if (pyidx == NULL) return NULL;
                return PyTuple_Pack(2, Py_None, pyidx);
            }
            break;
        case 't':
            if ((idx + 3 < length) && str[idx + 1] == 'r' && str[idx + 2] == 'u' && str[idx + 3] == 'e') {
                pyidx = PyInt_FromSsize_t(idx + 4);
                if (pyidx == NULL) return NULL;
                return PyTuple_Pack(2, Py_True, pyidx);
            }
            break;
        case 'f':
            if ((idx + 4 < length) && str[idx + 1] == 'a' && str[idx + 2] == 'l' && str[idx + 3] == 's' && str[idx + 4] == 'e') {
                pyidx = PyInt_FromSsize_t(idx + 5);
                if (pyidx == NULL) return NULL;
                return PyTuple_Pack(2, Py_False, pyidx);
            }
            break;
        case 'N':
            if ((idx + 2 < length) && str[idx + 1] == 'a' && str[idx + 2] == 'N') {
                return _parse_constant(s, "NaN", idx);
            }
            break;
        case 'I':
            if ((idx + 7 < length) && str[idx + 1] == 'n' && str[idx + 2] == 'f' && str[idx + 3] == 'i' && str[idx + 4] == 'n' && str[idx + 5] == 'i' && str[idx + 6] == 't' && str[idx + 7] == 'y') {
                return _parse_constant(s, "Infinity", idx);
            }
            break;
        case '-':
            if ((idx + 8 < length) && str[idx + 1] == 'I' && str[idx + 2] == 'n' && str[idx + 3] == 'f' && str[idx + 4] == 'i' && str[idx + 5] == 'n' && str[idx + 6] == 'i' && str[idx + 7] == 't' && str[idx + 8] == 'y') {
                return _parse_constant(s, "-Infinity", idx);
            }
            break;
    }
    return _match_number_str(s, pystr, idx);
}

static PyObject *
scan_once_unicode(PyScannerObject *s, PyObject *pystr, Py_ssize_t idx)
{
    Py_UNICODE *str = PyUnicode_AS_UNICODE(pystr);
    Py_ssize_t length = PyUnicode_GET_SIZE(pystr);
    PyObject *pyidx;
    if (idx >= length) {
        PyErr_SetNone(PyExc_StopIteration);
        return NULL;
    }
    switch (str[idx]) {
        case '"': 
            return scanstring_unicode(pystr, idx + 1,
                PyObject_IsTrue(s->strict));
        case '{':
            return _parse_object_unicode(s, pystr, idx + 1);
        case '[':
            return _parse_array_unicode(s, pystr, idx + 1);
        case 'n':
            if ((idx + 3 < length) && str[idx + 1] == 'u' && str[idx + 2] == 'l' && str[idx + 3] == 'l') {
                pyidx = PyInt_FromSsize_t(idx + 4);
                if (pyidx == NULL) return NULL;
                return PyTuple_Pack(2, Py_None, pyidx);
            }
            break;
        case 't':
            if ((idx + 3 < length) && str[idx + 1] == 'r' && str[idx + 2] == 'u' && str[idx + 3] == 'e') {
                pyidx = PyInt_FromSsize_t(idx + 4);
                if (pyidx == NULL) return NULL;
                return PyTuple_Pack(2, Py_True, pyidx);
            }
            break;
        case 'f':
            if ((idx + 4 < length) && str[idx + 1] == 'a' && str[idx + 2] == 'l' && str[idx + 3] == 's' && str[idx + 4] == 'e') {
                pyidx = PyInt_FromSsize_t(idx + 5);
                if (pyidx == NULL) return NULL;
                return PyTuple_Pack(2, Py_False, pyidx);
            }
            break;
        case 'N':
            if ((idx + 2 < length) && str[idx + 1] == 'a' && str[idx + 2] == 'N') {
                return _parse_constant(s, "NaN", idx);
            }
            break;
        case 'I':
            if ((idx + 7 < length) && str[idx + 1] == 'n' && str[idx + 2] == 'f' && str[idx + 3] == 'i' && str[idx + 4] == 'n' && str[idx + 5] == 'i' && str[idx + 6] == 't' && str[idx + 7] == 'y') {
                return _parse_constant(s, "Infinity", idx);
            }
            break;
        case '-':
            if ((idx + 8 < length) && str[idx + 1] == 'I' && str[idx + 2] == 'n' && str[idx + 3] == 'f' && str[idx + 4] == 'i' && str[idx + 5] == 'n' && str[idx + 6] == 'i' && str[idx + 7] == 't' && str[idx + 8] == 'y') {
                return _parse_constant(s, "-Infinity", idx);
            }
            break;
    }
    return _match_number_unicode(s, pystr, idx);
}

static PyObject *
scanner_call(PyObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *pystr;
    Py_ssize_t idx;
    static char *kwlist[] = {"string", "idx", NULL};
    PyScannerObject *s = (PyScannerObject *)self;
    assert(PyScanner_Check(self));
#if PY_VERSION_HEX < 0x02050000 
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "On:scan_once", kwlist, &pystr, &idx))
#else
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "Oi:scan_once", kwlist, &pystr, &idx))
#endif
        return NULL;
    if (PyString_Check(pystr)) {
        return scan_once_str(s, pystr, idx);
    }
    else if (PyUnicode_Check(pystr)) {
        return scan_once_unicode(s, pystr, idx);
    }
    PyErr_Format(PyExc_TypeError,
                 "first argument must be a string, not %.80s",
                 Py_TYPE(pystr)->tp_name);
    return NULL;
}

static int
scanner_init(PyObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *ctx;
    static char *kwlist[] = {"context", NULL};

    assert(PyScanner_Check(self));
    PyScannerObject *s = (PyScannerObject *)self;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O:make_scanner", kwlist, &ctx))
        return -1;

    s->encoding = NULL;
    s->strict = NULL;
    s->object_hook = NULL;
    s->parse_float = NULL;
    s->parse_int = NULL;
    s->parse_constant = NULL;
    s->encoding = PyObject_GetAttrString(ctx, "encoding");
    if (s->encoding == Py_None) {
        Py_DECREF(Py_None);
        s->encoding = PyString_InternFromString(DEFAULT_ENCODING);
    }
    if (s->encoding == NULL) goto bail;
    s->strict = PyObject_GetAttrString(ctx, "strict");
    if (s->strict == NULL) goto bail;
    s->object_hook = PyObject_GetAttrString(ctx, "object_hook");
    if (s->object_hook == NULL) goto bail;
    s->parse_float = PyObject_GetAttrString(ctx, "parse_float");
    if (s->parse_float == NULL) goto bail;
    s->parse_int = PyObject_GetAttrString(ctx, "parse_int");
    if (s->parse_int == NULL) goto bail;
    s->parse_constant = PyObject_GetAttrString(ctx, "parse_constant");
    if (s->parse_constant == NULL) goto bail;
    
    return 0;

bail:
    Py_XDECREF(s->encoding);
    Py_XDECREF(s->strict);
    Py_XDECREF(s->object_hook);
    Py_XDECREF(s->parse_float);
    Py_XDECREF(s->parse_int);
    Py_XDECREF(s->parse_constant);
    s->encoding = NULL;
    s->strict = NULL;
    s->object_hook = NULL;
    s->parse_float = NULL;
    s->parse_int = NULL;
    s->parse_constant = NULL;
    return -1;
}

PyDoc_STRVAR(scanner_doc, "JSON scanner object");

static
PyTypeObject PyScannerType = {
    PyObject_HEAD_INIT(0)
    0,                    /* tp_internal */
    "make_scanner",       /* tp_name */
    sizeof(PyScannerObject), /* tp_basicsize */
    0,                    /* tp_itemsize */
    scanner_dealloc, /* tp_dealloc */
    0,                    /* tp_print */
    0,                    /* tp_getattr */
    0,                    /* tp_setattr */
    0,                    /* tp_compare */
    0,                    /* tp_repr */
    0,                    /* tp_as_number */
    0,                    /* tp_as_sequence */
    0,                    /* tp_as_mapping */
    0,                    /* tp_hash */
    scanner_call,         /* tp_call */
    0,                    /* tp_str */
    PyObject_GenericGetAttr,                    /* tp_getattro */
    PyObject_GenericSetAttr,                    /* tp_setattro */
    0,                    /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,   /* tp_flags */
    scanner_doc,          /* tp_doc */
    0,                    /* tp_traverse */
    0,                    /* tp_clear */
    0,                    /* tp_richcompare */
    0,                    /* tp_weaklistoffset */
    0,                    /* tp_iter */
    0,                    /* tp_iternext */
    0,                    /* tp_methods */
    scanner_members,                    /* tp_members */
    0,                    /* tp_getset */
    0,                    /* tp_base */
    0,                    /* tp_dict */
    0,                    /* tp_descr_get */
    0,                    /* tp_descr_set */
    0,                    /* tp_dictoffset */
    scanner_init,                    /* tp_init */
    PyType_GenericAlloc,                    /* tp_alloc */
    PyType_GenericNew,          /* tp_new */
    _PyObject_Del,                    /* tp_free */
};

static PyMethodDef speedups_methods[] = {
    {"encode_basestring_ascii",
        (PyCFunction)py_encode_basestring_ascii,
        METH_O,
        pydoc_encode_basestring_ascii},
    {"scanstring",
        (PyCFunction)py_scanstring,
        METH_VARARGS,
        pydoc_scanstring},
    {NULL, NULL, 0, NULL}
};

PyDoc_STRVAR(module_doc,
"simplejson speedups\n");

void
init_speedups(void)
{
    PyObject *m;
    if (PyType_Ready(&PyScannerType) < 0)
        return;
    m = Py_InitModule3("_speedups", speedups_methods, module_doc);
    Py_INCREF((PyObject*)&PyScannerType);
    PyModule_AddObject(m, "make_scanner", (PyObject*)&PyScannerType);
}
