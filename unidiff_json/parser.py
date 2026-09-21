"""Parser from unified diff text into plain data objects.

Grammar, roughly:

    diff       := file+
    file       := "--- " old_path NEWLINE "+++ " new_path NEWLINE hunk+
    hunk       := hunk_header NEWLINE hunk_line*
    hunk_header:= "@@ -" old_start ["," old_count] " +" new_start ["," new_count] " @@" section?
    hunk_line  := (" " | "+" | "-") text | "\\" text

The body of a hunk is consumed until the running counts of old/new lines
match the counts declared in the header, which is what lets us tell the
difference between "this hunk is finished" and "the next file starts here".
"""

from dataclasses import dataclass, field

from .errors import DiffFormatError


@dataclass
class DiffLine:
    kind: str  # "context", "insert", "delete", or "marker" (no-newline notice)
    text: str


@dataclass
class Hunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    section: str
    lines: list = field(default_factory=list)


@dataclass
class FileDiff:
    old_path: str
    new_path: str
    hunks: list = field(default_factory=list)


def parse_unified_diff(text):
    """Parse unified diff text into a list of FileDiff objects.

    Raises DiffFormatError on the first structural problem found.
    """
    lines = text.splitlines()
    n = len(lines)
    i = 0
    files = []

    while i < n:
        if lines[i].strip() == "":
            i += 1
            continue

        if not lines[i].startswith("--- "):
            raise DiffFormatError(
                f"expected a file header starting with '--- ', got {lines[i]!r}",
                i + 1, 1, lines[i],
            )
        old_path = lines[i][4:].split("\t", 1)[0].strip()
        i += 1

        if i >= n or not lines[i].startswith("+++ "):
            got_line = lines[i] if i < n else ""
            raise DiffFormatError(
                "expected the matching '+++ ' header right after a '--- ' header",
                i + 1 if i < n else max(n, 1), 1, got_line,
            )
        new_path = lines[i][4:].split("\t", 1)[0].strip()
        i += 1

        hunks = []
        while i < n and lines[i].startswith("@@"):
            hunk, i = _parse_hunk(lines, i, n)
            hunks.append(hunk)

        if not hunks:
            got_line = lines[i] if i < n else ""
            raise DiffFormatError(
                "file header is not followed by any '@@' hunk",
                i + 1 if i < n else max(n, 1), 1, got_line,
            )

        files.append(FileDiff(old_path, new_path, hunks))

    if not files:
        raise DiffFormatError(
            "input does not contain a '--- ' file header", 1, 1, "",
        )

    return files


_DIGITS = "0123456789"


def _parse_hunk_header(header, line_no):
    """Walk a hunk header against '@@ -S[,C] +S[,C] @@[ section]' by hand.

    A regex could do the matching, but it can't say *where* a bad header
    stopped matching. Walking it by hand means the failure position doubles
    as the column we report in the error.
    """
    pos = 0

    def fail(message):
        raise DiffFormatError(message, line_no, pos + 1, header)

    def literal(lit):
        nonlocal pos
        if header[pos:pos + len(lit)] != lit:
            return False
        pos += len(lit)
        return True

    def digits(what):
        nonlocal pos
        start = pos
        while pos < len(header) and header[pos] in _DIGITS:
            pos += 1
        if pos == start:
            fail(f"expected one or more digits for the {what} line number")
        return int(header[start:pos])

    def optional_count():
        nonlocal pos
        if pos < len(header) and header[pos] == ",":
            pos += 1
            return digits("count")
        return None

    if not literal("@@ -"):
        fail("malformed hunk header, expected it to start with '@@ -'")
    old_start = digits("old")
    old_count = optional_count()
    if old_count is None:
        old_count = 1

    if not literal(" +"):
        fail("expected ' +' to separate the old and new line ranges")
    new_start = digits("new")
    new_count = optional_count()
    if new_count is None:
        new_count = 1

    if not literal(" @@"):
        fail("expected the hunk header to close with ' @@'")

    section = header[pos:].strip()
    return old_start, old_count, new_start, new_count, section


def _parse_hunk(lines, i, n):
    header = lines[i]
    header_line_no = i + 1
    old_start, old_count, new_start, new_count, section = _parse_hunk_header(header, header_line_no)
    i += 1

    diff_lines = []
    old_seen = 0
    new_seen = 0

    while old_seen < old_count or new_seen < new_count:
        if i >= n:
            raise DiffFormatError(
                f"hunk starting at line {header_line_no} ends early: expected "
                f"{old_count} old line(s) and {new_count} new line(s), got "
                f"{old_seen} and {new_seen}",
                n, 1, lines[n - 1] if n else "",
            )
        raw = lines[i]

        if raw.startswith("\\"):
            diff_lines.append(DiffLine("marker", raw[1:].strip()))
            i += 1
            continue

        kind_char = raw[0] if raw else " "
        text = raw[1:] if raw else ""

        if kind_char == " ":
            if old_seen >= old_count or new_seen >= new_count:
                break
            diff_lines.append(DiffLine("context", text))
            old_seen += 1
            new_seen += 1
        elif kind_char == "-":
            if old_seen >= old_count:
                raise DiffFormatError(
                    f"hunk header declares {old_count} old line(s) but a "
                    f"{old_seen + 1}th '-' line appears here",
                    i + 1, 1, raw,
                )
            diff_lines.append(DiffLine("delete", text))
            old_seen += 1
        elif kind_char == "+":
            if new_seen >= new_count:
                raise DiffFormatError(
                    f"hunk header declares {new_count} new line(s) but a "
                    f"{new_seen + 1}th '+' line appears here",
                    i + 1, 1, raw,
                )
            diff_lines.append(DiffLine("insert", text))
            new_seen += 1
        else:
            raise DiffFormatError(
                f"expected a line starting with ' ', '+', '-', or '\\', got {kind_char!r}",
                i + 1, 1, raw,
            )
        i += 1

    hunk = Hunk(old_start, old_count, new_start, new_count, section, diff_lines)
    return hunk, i
