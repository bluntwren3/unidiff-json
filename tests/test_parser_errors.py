"""Every DiffFormatError raise site in unidiff_json.parser, pinned to the
exact line/column it should report. Each test builds its input from a list
of lines joined with "\n" rather than a triple-quoted blob, so the line
count used to predict the error location can't drift from what's on screen.
"""

import unittest

from unidiff_json.errors import DiffFormatError
from unidiff_json.parser import parse_unified_diff


def diff(*lines):
    return "\n".join(lines) + "\n"


class ParserErrorTests(unittest.TestCase):
    def assert_fails(self, text, line, column, source_line):
        with self.assertRaises(DiffFormatError) as ctx:
            parse_unified_diff(text)
        exc = ctx.exception
        self.assertEqual(exc.line, line)
        self.assertEqual(exc.column, column)
        self.assertEqual(exc.source_line, source_line)
        return exc

    def test_empty_input(self):
        self.assert_fails("", 1, 1, "")

    def test_blank_only_input(self):
        self.assert_fails("   \n\n", 1, 1, "")

    def test_missing_old_header(self):
        self.assert_fails(diff("foo"), 1, 1, "foo")

    def test_missing_new_header_at_eof(self):
        self.assert_fails(diff("--- a"), 1, 1, "")

    def test_missing_new_header_with_trailing_line(self):
        self.assert_fails(diff("--- a", "foo"), 2, 1, "foo")

    def test_file_header_without_hunk_at_eof(self):
        self.assert_fails(diff("--- a", "+++ b"), 2, 1, "")

    def test_file_header_without_hunk_with_trailing_line(self):
        self.assert_fails(diff("--- a", "+++ b", "foo"), 3, 1, "foo")

    def test_hunk_stops_once_counts_are_met(self):
        # The hunk header promises one old and one new line; the second
        # " a" line is never pulled into the hunk body, so it is seen
        # by the outer loop as a bogus start of the next file.
        exc = self.assert_fails(
            diff("--- a", "+++ b", "@@ -1,1 +1,1 @@", " a", " a"),
            5, 1, " a",
        )
        self.assertIn("expected a file header", exc.message)

    def test_hunk_header_bad_prefix(self):
        exc = self.assert_fails(
            diff("--- a", "+++ b", "@@ x"),
            3, 1, "@@ x",
        )
        self.assertIn("expected it to start with '@@ -'", exc.message)

    def test_hunk_header_missing_old_digits(self):
        exc = self.assert_fails(
            diff("--- a", "+++ b", "@@ -a,3 +1,3 @@"),
            3, 5, "@@ -a,3 +1,3 @@",
        )
        self.assertIn("old line number", exc.message)

    def test_hunk_header_missing_plus_separator(self):
        exc = self.assert_fails(
            diff("--- a", "+++ b", "@@ -1,3 x1,3 @@"),
            3, 8, "@@ -1,3 x1,3 @@",
        )
        self.assertIn("expected ' +'", exc.message)

    def test_hunk_header_missing_new_digits(self):
        exc = self.assert_fails(
            diff("--- a", "+++ b", "@@ -1,3 +x,3 @@"),
            3, 10, "@@ -1,3 +x,3 @@",
        )
        self.assertIn("new line number", exc.message)

    def test_hunk_header_missing_closing_marker(self):
        exc = self.assert_fails(
            diff("--- a", "+++ b", "@@ -1 +1 XX"),
            3, 9, "@@ -1 +1 XX",
        )
        self.assertIn("close with ' @@'", exc.message)

    def test_hunk_ends_early(self):
        exc = self.assert_fails(
            diff("--- a", "+++ b", "@@ -1,2 +1,2 @@", " line1"),
            4, 1, " line1",
        )
        self.assertIn("ends early", exc.message)
        self.assertIn("got 1 and 1", exc.message)

    def test_too_many_delete_lines(self):
        exc = self.assert_fails(
            diff("--- a", "+++ b", "@@ -1,1 +1,2 @@", "-a", "-b"),
            5, 1, "-b",
        )
        self.assertIn("declares 1 old line(s)", exc.message)

    def test_too_many_insert_lines(self):
        exc = self.assert_fails(
            diff("--- a", "+++ b", "@@ -1,2 +1,1 @@", "+a", "+b"),
            5, 1, "+b",
        )
        self.assertIn("declares 1 new line(s)", exc.message)

    def test_invalid_line_prefix(self):
        exc = self.assert_fails(
            diff("--- a", "+++ b", "@@ -1,1 +1,1 @@", "xa"),
            4, 1, "xa",
        )
        self.assertIn("got 'x'", exc.message)


class DiffFormatErrorStrTests(unittest.TestCase):
    def test_str_includes_caret_pointing_at_column(self):
        exc = DiffFormatError("bad thing", 3, 5, "@@ -a,3 +1,3 @@")
        text = str(exc)
        lines = text.splitlines()
        self.assertEqual(lines[0], "line 3, column 5: bad thing")
        self.assertTrue(lines[2].endswith("^"))
        # both the source line and the pointer line get a 4-space indent,
        # so the caret sits at 4 + (column - 1) to land under the right char
        self.assertEqual(len(lines[2]) - len(lines[2].lstrip(" ")), 8)

    def test_str_without_source_line_has_no_caret(self):
        exc = DiffFormatError("bad thing", 1, 1, "")
        self.assertEqual(str(exc), "line 1, column 1: bad thing")


if __name__ == "__main__":
    unittest.main()
