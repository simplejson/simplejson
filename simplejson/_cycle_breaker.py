"""Cycle breaker for the mutually recursive encoder closures.

This module exists separately because it uses ``nonlocal``, which is
a syntax error on Python 2.  Importing it only on Python 3 keeps
the encoder module loadable on both versions.
"""


def _wrap_iterencode_once(_iterencode, _iterencode_dict, _iterencode_list):
    """Return a wrapper generator that delegates to *_iterencode* and
    then breaks the reference cycle between the three closures."""
    def _iterencode_once(o, _current_indent_level):
        nonlocal _iterencode, _iterencode_dict, _iterencode_list
        try:
            for chunk in _iterencode(o, _current_indent_level):
                yield chunk
        finally:
            del _iterencode, _iterencode_dict, _iterencode_list
    return _iterencode_once
