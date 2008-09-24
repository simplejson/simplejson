"""
Iterator based sre token scanner
"""
import re
from re import VERBOSE, MULTILINE, DOTALL

__all__ = ['make_scanner']

FLAGS = (VERBOSE | MULTILINE | DOTALL)


NUMBER_PATTERN = r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?'

def make_scanner(lexicon):
    parse_object = lexicon['object']
    parse_array = lexicon['array']
    parse_string = lexicon['string']
    match_number = re.compile(NUMBER_PATTERN, FLAGS).match

    def _scan_once(string, idx, context):
        try:
            nextchar = string[idx]
        except IndexError:
            raise StopIteration
        
        if nextchar == '"':
            return parse_string(string, idx + 1, context.encoding, context.strict)
        elif nextchar == '{':
            return parse_object((string, idx + 1), context)
        elif nextchar == '[':
            return parse_array((string, idx + 1), context)
        elif nextchar == 'n' and string[idx:idx + 4] == 'null':
            return None, idx + 4
        elif nextchar == 't' and string[idx:idx + 4] == 'true':
            return True, idx + 4
        elif nextchar == 'f' and string[idx:idx + 5] == 'false':
            return False, idx + 5
        
        m = match_number(string, idx)
        if m is not None:
            integer, frac, exp = m.groups()
            if frac or exp:
                res = context.parse_float(integer + (frac or '') + (exp or ''))
            else:
                res = context.parse_int(integer)
            return res, m.end()
        elif nextchar == 'N' and string[idx:idx + 3] == 'NaN':
            return context.parse_constant('NaN'), idx + 3
        elif nextchar == 'I' and string[idx:idx + 8] == 'Infinity':
            return context.parse_constant('Infinity'), idx + 8
        elif nextchar == '-' and string[idx:idx + 9] == '-Infinity':
            return context.parse_constant('-Infinity'), idx + 9
        else:
            raise StopIteration
    
    return _scan_once