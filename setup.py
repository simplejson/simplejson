#!/usr/bin/env python
from __future__ import with_statement

import os
import sys
try:
    from setuptools import setup, Extension, Command
except ImportError:
    from distutils.core import setup, Extension, Command
from distutils.command.build_ext import build_ext
from distutils.errors import CCompilerError, DistutilsExecError, \
    DistutilsPlatformError

IS_PYPY = hasattr(sys, 'pypy_translation_info')
IS_GRAALPY = getattr(getattr(sys, "implementation", None), "name", None) == "graalpy"
VERSION = '3.20.2'
DESCRIPTION = "Simple, fast, extensible JSON encoder/decoder for Python"

with open('README.rst', 'r') as f:
    LONG_DESCRIPTION = f.read()

PYTHON_REQUIRES = '>=2.5, !=3.0.*, !=3.1.*, !=3.2.*'

CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'License :: OSI Approved :: Academic Free License (AFL)',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.5',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
    'Programming Language :: Python :: 3.12',
    'Programming Language :: Python :: 3.13',
    'Programming Language :: Python :: Implementation :: CPython',
    'Programming Language :: Python :: Implementation :: PyPy',
    'Topic :: Software Development :: Libraries :: Python Modules',
]

if sys.platform == 'win32' and sys.version_info < (2, 7):
    # 2.6's distutils.msvc9compiler can raise an IOError when failing to
    # find the compiler
    # It can also raise ValueError https://bugs.python.org/issue7511
    ext_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError,
                  IOError, ValueError)
else:
    ext_errors = (CCompilerError, DistutilsExecError, DistutilsPlatformError)


class BuildFailed(Exception):
    pass


class ve_build_ext(build_ext):
    # This class allows C extension building to fail.

    def run(self):
        try:
            build_ext.run(self)
        except DistutilsPlatformError:
            raise BuildFailed()

    def build_extension(self, ext):
        try:
            build_ext.build_extension(self, ext)
        except ext_errors:
            raise BuildFailed()


class TestCommand(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import sys
        import subprocess
        raise SystemExit(
            subprocess.call([sys.executable,
                             # Turn on deprecation warnings
                             '-Wd',
                             'simplejson/tests/__init__.py']))


def run_setup(with_binary):
    cmdclass = dict(test=TestCommand)
    if with_binary:
        kw = dict(
            ext_modules=[
                Extension("simplejson._speedups", ["simplejson/_speedups.c"]),
            ],
            cmdclass=dict(cmdclass, build_ext=ve_build_ext),
        )
    else:
        kw = dict(cmdclass=cmdclass)

    setup(
        name="simplejson",
        version=VERSION,
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        classifiers=CLASSIFIERS,
        python_requires=PYTHON_REQUIRES,
        author="Bob Ippolito",
        author_email="bob@redivi.com",
        url="https://github.com/simplejson/simplejson",
        license="MIT License",
        packages=['simplejson', 'simplejson.tests'],
        platforms=['any'],
        **kw)


DISABLE_SPEEDUPS = IS_PYPY or IS_GRAALPY or os.environ.get('DISABLE_SPEEDUPS') == '1'
CIBUILDWHEEL = os.environ.get('CIBUILDWHEEL') == '1'
REQUIRE_SPEEDUPS = CIBUILDWHEEL or os.environ.get('REQUIRE_SPEEDUPS') == '1'
try:
    run_setup(not DISABLE_SPEEDUPS)
except BuildFailed:
    if REQUIRE_SPEEDUPS:
        raise
    BUILD_EXT_WARNING = ("WARNING: The C extension could not be compiled, "
                         "speedups are not enabled.")
    print('*' * 75)
    print(BUILD_EXT_WARNING)
    print("Failure information, if any, is above.")
    print("I'm retrying the build without the C extension now.")
    print('*' * 75)

    run_setup(False)

    print('*' * 75)
    print(BUILD_EXT_WARNING)
    print("Plain-Python installation succeeded.")
    print('*' * 75)
