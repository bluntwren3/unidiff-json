import argparse
import sys

from .errors import DiffFormatError
from .parser import parse_unified_diff
from . import serializer


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="unidiff-json",
        description="Convert between unified diff text and unidiff-json documents.",
    )
    parser.add_argument("input", nargs="?", help="input file, or omitted/'-' for stdin")
    parser.add_argument("--to", choices=("json", "diff"), required=True, help="target format")
    parser.add_argument("-o", "--output", help="output file, default stdout")
    args = parser.parse_args(argv)

    if args.input and args.input != "-":
        with open(args.input, "r") as fh:
            text = fh.read()
    else:
        text = sys.stdin.read()

    try:
        if args.to == "json":
            files = parse_unified_diff(text)
            result = serializer.dumps(files)
        else:
            files = serializer.loads(text)
            result = serializer.to_unified_diff(files)
    except DiffFormatError as exc:
        print(f"unidiff-json: {exc}", file=sys.stderr)
        return 1
    except (ValueError, KeyError) as exc:
        print(f"unidiff-json: input is not a valid unidiff-json document: {exc}", file=sys.stderr)
        return 1

    if args.output:
        with open(args.output, "w") as fh:
            fh.write(result)
    else:
        sys.stdout.write(result)
    return 0
