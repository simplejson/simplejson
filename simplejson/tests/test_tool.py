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

    def runTool(self, args=None, data=None, env=None):
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
        self.assertEqual(strip_python_stderr(err), ''.encode())
        self.assertEqual(proc.returncode, 0)
        return out.decode('utf8').splitlines()

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
            infile.close()
            os.unlink(infile_name)

    def assert_failed_input_preserves_output(self, same_file=False,
                                            missing_input=False):
        if sys.platform == 'emscripten':
            self.skipTest("subprocess not available on Emscripten")
        infile, infile_name = open_temp_file()
        outfile, outfile_name = open_temp_file()
        invalid_json = b'{invalid json'
        old_output = b'previous output\n'
        try:
            infile.write(invalid_json)
            infile.close()
            outfile.write(old_output)
            outfile.close()
            output_name = infile_name if same_file else outfile_name
            input_name = infile_name
            if missing_input:
                # Use a non-existent child of a newly created empty directory.
                directory = tempfile.mkdtemp()
                input_name = os.path.join(directory, 'missing.json')
            try:
                proc = subprocess.Popen(
                    [sys.executable, '-m', 'simplejson.tool',
                     input_name, output_name],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, err = proc.communicate()
                self.assertNotEqual(proc.returncode, 0)
                self.assertEqual(out, b'')
                self.assertTrue(strip_python_stderr(err))
                if not missing_input:
                    self.assertIn(b'Expecting property name', err)
                with open(output_name, 'rb') as f:
                    self.assertEqual(f.read(),
                                     invalid_json if same_file else old_output)
            finally:
                if missing_input:
                    os.rmdir(directory)
        finally:
            infile.close()
            outfile.close()
            os.unlink(infile_name)
            os.unlink(outfile_name)

    def test_invalid_input_preserves_output(self):
        self.assert_failed_input_preserves_output()

    def test_invalid_input_preserves_same_file(self):
        self.assert_failed_input_preserves_output(same_file=True)

    def test_missing_input_preserves_output(self):
        self.assert_failed_input_preserves_output(missing_input=True)
