#!/usr/bin/env python

import sys
try:
    import setuptools
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()

from setuptools import setup, find_packages, Extension, Feature
from distutils.command.build_ext import build_ext
from distutils.errors import CCompilerError, DistutilsExecError, \
    DistutilsPlatformError

IS_PYPY = hasattr(sys, 'pypy_translation_info')
VERSION = '2.1.6'
DESCRIPTION = "Simple, fast, extensible JSON encoder/decoder for Python"
LONG_DESCRIPTION = open('README.rst', 'r').read()

CLASSIFIERS = filter(None, map(str.strip,
"""
Intended Audience :: Developers
License :: OSI Approved :: MIT License
Programming Language :: Python
Topic :: Software Development :: Libraries :: Python Modules
""".splitlines()))


speedups = Feature(
    "optional C speed-enhancement module",
    standard=True,
    ext_modules = [
        Extension("simplejson._speedups", ["simplejson/_speedups.c"]),
    ],
)

if sys.platform == 'win32' and sys.version_info > (2, 6):
   # 2.6's distutils.msvc9compiler can raise an IOError when failing to
   # find the compiler
   ext_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError,
                 IOError)
else:
   ext_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError)

class BuildFailed(Exception):
    pass

class ve_build_ext(build_ext):
    # This class allows C extension building to fail.

    def run(self):
        try:
            build_ext.run(self)
        except DistutilsPlatformError, x:
            raise BuildFailed()

    def build_extension(self, ext):
        try:
            build_ext.build_extension(self, ext)
        except ext_errors, x:
            raise BuildFailed()

def run_setup(with_binary):
    if with_binary:
        features = {'speedups': speedups}
    else:
        features = {}

    setup(
        name="simplejson",
        version=VERSION,
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        classifiers=CLASSIFIERS,
        author="Bob Ippolito",
        author_email="bob@redivi.com",
        url="http://github.com/simplejson/simplejson",
        license="MIT License",
        packages=find_packages(exclude=['ez_setup']),
        platforms=['any'],
        test_suite="simplejson.tests.all_tests_suite",
        zip_safe=True,
        features=features,
        cmdclass={'build_ext': ve_build_ext},
    )

try:
    run_setup(not IS_PYPY)
except BuildFailed:
    BUILD_EXT_WARNING = "WARNING: The C extension could not be compiled, speedups are not enabled."
    print '*' * 75
    print BUILD_EXT_WARNING
    print "Failure information, if any, is above."
    print "I'm retrying the build without the C extension now."
    print '*' * 75

    run_setup(False)

    print '*' * 75
    print BUILD_EXT_WARNING
    print "Plain-Python installation succeeded."
    print '*' * 75
