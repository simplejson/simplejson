import os
import re
import sys
import textwrap
import unittest
import subprocess
import tempfile

def strip_python_stderr(stderr):
    """Strip debug-build refcount output from stderr."""
    return re.sub(b"\\[\\d+ refs\\]\\r?\\n?$", b"", stderr).strip()

def open_temp_file():
    file = tempfile.NamedTemporaryFile(delete=False)
    filename = file.name
    return file, filename

class TestTool(unittest.TestCase):
    data = """

        [["blorpie"],[ "whoops" ] , [
                                 ],\t"d-shtaeou",\r"d-nthiouh",
        "i-vhbjkhnth", {"nifty":87}, {"morefield" :\tfalse,"field"
            :"yes"}  ]
           """

    expect = textwrap.dedent("""\
    [
        [
            "blorpie"
        ],
        [
            "whoops"
        ],
        [],
        "d-shtaeou",
        "d-nthiouh",
        "i-vhbjkhnth",
        {
            "nifty": 87
        },
        {
            "field": "yes",
            "morefield": false
        }
    ]
    """)

    def runToolProcess(self, args=None, data=None, env=None):
        if sys.platform == 'emscripten':
            self.skipTest("subprocess not available on Emscripten")
        argv = [sys.executable, '-m', 'simplejson.tool']
        if args:
            argv.extend(args)
        proc = subprocess.Popen(argv,
                                stdin=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                env=env)
        out, err = proc.communicate(data)
        return proc.returncode, out, strip_python_stderr(err)

    def runTool(self, args=None, data=None, env=None):
        returncode, out, err = self.runToolProcess(args, data, env)
        self.assertEqual(err, ''.encode())
        self.assertEqual(returncode, 0)
        return out.decode('utf8').splitlines()

    def runToolFailure(self, args):
        """Run the tool expecting a clean failure: a one-line error
        message on stderr, no traceback, and nothing on stdout."""
        returncode, out, err = self.runToolProcess(args)
        self.assertNotEqual(returncode, 0)
        self.assertEqual(out, b'')
        self.assertTrue(err)
        self.assertNotIn(b'Traceback', err)
        return err

    def test_stdin_stdout(self):
        self.assertEqual(
            self.runTool(data=self.data.encode()),
            self.expect.splitlines())

    def test_infile_stdout(self):
        infile, infile_name = open_temp_file()
        try:
            infile.write(self.data.encode())
            infile.close()
            self.assertEqual(
                self.runTool(args=[infile_name]),
                self.expect.splitlines())
        finally:
            os.unlink(infile_name)

    def assert_utf8_infile(self, use_outfile):
        infile, infile_name = open_temp_file()
        outfile, outfile_name = open_temp_file()
        try:
            infile.write(b'{"\xc3\xa4": "\xf0\x9f\x9a\x80"}')
            infile.close()
            outfile.close()
            args = [infile_name]
            if use_outfile:
                args.append(outfile_name)
            # Keep standard streams in UTF-8 without changing file I/O defaults.
            env = dict(os.environ, PYTHONUTF8='0', PYTHONIOENCODING='utf-8',
                       LC_ALL='C', PYTHONCOERCECLOCALE='0')
            lines = self.runTool(args=args, env=env)
            if use_outfile:
                self.assertEqual(lines, [])
                with open(outfile_name, 'rb') as f:
                    lines = f.read().decode('utf8').splitlines()
            self.assertEqual(lines, [
                '{', '    "\\u00e4": "\\ud83d\\ude80"', '}'])
        finally:
            infile.close()
            outfile.close()
            os.unlink(infile_name)
            os.unlink(outfile_name)

    def test_utf8_infile_stdout(self):
        self.assert_utf8_infile(use_outfile=False)

    def test_utf8_infile_outfile(self):
        self.assert_utf8_infile(use_outfile=True)

    def test_infile_outfile(self):
        infile, infile_name = open_temp_file()
        try:
            infile.write(self.data.encode())
            infile.close()
            # outfile will get overwritten by tool, so the delete
            # may not work on some platforms. Do it manually.
            outfile, outfile_name = open_temp_file()
            try:
                outfile.close()
                self.assertEqual(
                    self.runTool(args=[infile_name, outfile_name]),
                    [])
                with open(outfile_name, 'rb') as f:
                    self.assertEqual(
                        f.read().decode('utf8').splitlines(),
                        self.expect.splitlines()
                    )
            finally:
                os.unlink(outfile_name)
        finally:
            os.unlink(infile_name)

    def test_infile_is_outfile(self):
        infile, infile_name = open_temp_file()
        try:
            infile.write(self.data.encode())
            infile.close()
            self.assertEqual(self.runTool(args=[infile_name, infile_name]), [])
            with open(infile_name, 'rb') as f:
                self.assertEqual(f.read().decode('utf8').splitlines(),
                                 self.expect.splitlines())
        finally:
            os.unlink(infile_name)

    def test_invalid_input_preserves_outfile(self):
        infile, infile_name = open_temp_file()
        outfile, outfile_name = open_temp_file()
        try:
            infile.write(b'{invalid json')
            infile.close()
            outfile.write(b'previous output\n')
            outfile.close()
            err = self.runToolFailure([infile_name, outfile_name])
            self.assertIn(b'Expecting property name', err)
            with open(outfile_name, 'rb') as f:
                self.assertEqual(f.read(), b'previous output\n')
        finally:
            os.unlink(infile_name)
            os.unlink(outfile_name)

    def test_invalid_input_preserves_infile_is_outfile(self):
        infile, infile_name = open_temp_file()
        try:
            infile.write(b'{invalid json')
            infile.close()
            err = self.runToolFailure([infile_name, infile_name])
            self.assertIn(b'Expecting property name', err)
            with open(infile_name, 'rb') as f:
                self.assertEqual(f.read(), b'{invalid json')
        finally:
            os.unlink(infile_name)

    def test_missing_infile_is_clean_error(self):
        outfile, outfile_name = open_temp_file()
        try:
            outfile.write(b'previous output\n')
            outfile.close()
            self.runToolFailure([outfile_name + '.missing', outfile_name])
            with open(outfile_name, 'rb') as f:
                self.assertEqual(f.read(), b'previous output\n')
        finally:
            os.unlink(outfile_name)

    def test_unopenable_outfile_is_clean_error(self):
        infile, infile_name = open_temp_file()
        directory = tempfile.mkdtemp()
        try:
            infile.write(self.data.encode())
            infile.close()
            missing_dir = os.path.join(directory, 'missing')
            self.runToolFailure(
                [infile_name, os.path.join(missing_dir, 'out.json')])
            self.assertFalse(os.path.exists(missing_dir))
        finally:
            os.unlink(infile_name)
            os.rmdir(directory)
