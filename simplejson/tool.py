r"""Command-line tool to validate and pretty-print JSON

Usage::

    $ echo '{"json":"obj"}' | python -m simplejson.tool
    {
        "json": "obj"
    }
    $ echo '{ 1.2:3.4}' | python -m simplejson.tool
    Expecting property name: line 1 column 2 (char 2)

"""
import sys
import simplejson as json

def main():
    if len(sys.argv) > 3:
        raise SystemExit(sys.argv[0] + " [infile [outfile]]")
    infile_name = sys.argv[1] if len(sys.argv) > 1 else None
    outfile_name = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        if infile_name is None:
            infile = sys.stdin
        else:
            infile = open(infile_name, 'rb')
    except (IOError, OSError):
        raise SystemExit(sys.exc_info()[1])
    with infile:
        try:
            obj = json.load(infile,
                            object_pairs_hook=json.OrderedDict,
                            use_decimal=True)
        except ValueError:
            raise SystemExit(sys.exc_info()[1])
    # Open the output only after the input is parsed and closed, so a bad
    # input (or infile == outfile) never truncates the output.
    try:
        if outfile_name is None:
            outfile = sys.stdout
        else:
            outfile = open(outfile_name, 'w')
    except (IOError, OSError):
        raise SystemExit(sys.exc_info()[1])
    with outfile:
        json.dump(obj, outfile, sort_keys=True, indent='    ', use_decimal=True)
        outfile.write('\n')


if __name__ == '__main__':
    main()
