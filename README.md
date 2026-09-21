# unidiff-json

Unified diffs (the `--- a/file` / `+++ b/file` / `@@ ... @@` format that `diff -u`
and `git diff` produce) are fine to read but annoying to work with in code. Every
tool ends up writing its own ad-hoc regex-based scraper, and most of them fall
over silently on edge cases like hunks with no trailing newline, empty context
lines, or a hunk header whose counts don't match its body.

This is a small converter that goes the other way: parse unified diff text into
a plain JSON document with one object per file, one object per hunk, and one
object per line, and back again. The JSON form is meant to be something you'd
actually want to `jq` through or feed to another program, not just a dump of
Python's internal state.

The other half of the point: when the input is malformed, you get a line
number, a column number, and a caret pointing at the exact character, instead
of a stack trace or a silent wrong answer.

## Example

Input (`example.diff`):

```
--- a/greeting.py
+++ b/greeting.py
@@ -1,3 +1,3 @@
 def hello():
-    print("hi")
+    print("hello")
 hello()
```

Convert to JSON:

```
$ python -m unidiff_json example.diff --to json
{
  "format": "unidiff-json/v1",
  "files": [
    {
      "old_path": "a/greeting.py",
      "new_path": "b/greeting.py",
      "hunks": [
        {
          "old_start": 1,
          "old_count": 3,
          "new_start": 1,
          "new_count": 3,
          "section": "",
          "lines": [
            {"type": "context", "text": "def hello():"},
            {"type": "delete", "text": "    print(\"hi\")"},
            {"type": "insert", "text": "    print(\"hello\")"},
            {"type": "context", "text": "hello()"}
          ]
        }
      ]
    }
  ]
}
```

And back:

```
$ python -m unidiff_json example.json --to diff
```

produces byte-for-byte the same hunk body (whitespace inside lines is
preserved exactly; only the file's trailing newline is normalized).

## Error messages

Given a hunk header that claims 3 old lines but only has 2 in its body:

```
$ python -m unidiff_json broken.diff --to json
unidiff-json: line 7, column 1: hunk starting at line 4 ends early: expected 3 old line(s) and 3 new line(s), got 2 and 3
    hello()
    ^
```

Given a malformed hunk header:

```
$ python -m unidiff_json broken.diff --to json
unidiff-json: line 4, column 5: expected one or more digits for the old line number
    @@ -a,3 +1,3 @@
        ^
```

Every `DiffFormatError` carries `.line`, `.column`, and `.source_line` so a
caller can build its own reporting instead of printing the exception.

## Library usage

```python
from unidiff_json import parse_unified_diff, dumps

files = parse_unified_diff(open("example.diff").read())
print(dumps(files))
```

## Status

Early skeleton. The parser handles the common case (standard `diff -u` /
`git diff` output, including "no newline at end of file" markers) but has not
been fuzzed against every diff tool's quirks yet. See the roadmap in the repo
description for what's next.

## Install

No dependencies beyond the standard library. Clone it and run
`python -m unidiff_json` directly, or `pip install -e .` to get the
`unidiff-json` console script.
