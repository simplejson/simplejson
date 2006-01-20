#!/usr/bin/env python

import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages

VERSION = '1.3'
DESCRIPTION = "Simple, fast, extensible JSON encoder/decoder for Python"
LONG_DESCRIPTION = """
simplejson is a simple, fast, complete, correct and extensible
JSON <http://json.org> encoder and decoder for Python 2.3+.  It is
pure Python code with no dependencies.

simplejson was formerly known as simple_json, but changed its name to
comply with PEP 8 module naming guidelines.

The encoder may be subclassed to provide serialization in any kind of
situation, without any special support by the objects to be serialized
(somewhat like pickle).

The decoder can handle incoming JSON strings of any specified encoding
(UTF-8 by default).
"""

CLASSIFIERS = filter(None, map(str.strip,
"""                 
Intended Audience :: Developers
License :: OSI Approved :: MIT License
Programming Language :: Python
Topic :: Software Development :: Libraries :: Python Modules
""".splitlines()))

setup(
    name="simplejson",
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    classifiers=CLASSIFIERS,
    author="Bob Ippolito",
    author_email="bob@redivi.com",
    url="http://undefined.org/python/#simplejson",
    license="MIT License",
    packages=find_packages(exclude=['ez_setup']),
    platforms=['any'],
    test_suite="nose.collector",
    zip_safe=True,
    entry_points={
        'paste.filter_app_factory': ['json = simplejson.jsonfilter:factory'],
    },
)
