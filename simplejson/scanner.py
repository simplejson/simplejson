"""
Iterator based sre token scanner
"""
import re
from re import VERBOSE, MULTILINE, DOTALL
import sre_parse
import sre_compile
import sre_constants
from sre_constants import BRANCH, SUBPATTERN

__all__ = ['make_scanner', 'pattern']

FLAGS = (VERBOSE | MULTILINE | DOTALL)

def make_scanner(lexicon, flags=FLAGS):
    actions = [None]
    # Combine phrases into a compound pattern
    s = sre_parse.Pattern()
    s.flags = flags
    charpatterns = {}
    p = []
    idx = 0
    for token in lexicon:
        if token.pattern in (r'\[', r'{', r'"'):
            charpatterns[token.pattern[-1]] = token
        idx += 1
        phrase = token.pattern
        try:
            subpattern = sre_parse.SubPattern(s,
                [(SUBPATTERN, (idx, sre_parse.parse(phrase, flags)))])
        except sre_constants.error:
            raise
        p.append(subpattern)
        actions.append(token)

    s.groups = len(p) + 1 # NOTE(guido): Added to make SRE validation work
    p = sre_parse.SubPattern(s, [(BRANCH, (None, p))])
    scanner = sre_compile.compile(p).scanner

    def _scan_once(string, idx=0, context=None):
        try:
            action = charpatterns[string[idx]]
        except KeyError:
            pass
        except IndexError:
            raise StopIteration
        else:
            return action((string, idx + 1), context)
        
        m = scanner(string, idx).match()
        if m is None or m.end() == idx:
            raise StopIteration
        return actions[m.lastindex](m, context)
    
    return _scan_once

def pattern(pattern, flags=FLAGS):
    def decorator(fn):
        fn.pattern = pattern
        fn.regex = re.compile(pattern, flags)
        return fn
    return decorator