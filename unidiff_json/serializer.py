"""Conversion between the parsed diff objects and the JSON document format,
plus rendering the objects back out as unified diff text.
"""

import json

from .parser import DiffLine, FileDiff, Hunk

FORMAT_NAME = "unidiff-json/v1"

_KIND_TO_PREFIX = {"context": " ", "insert": "+", "delete": "-"}


def to_json_doc(files):
    return {
        "format": FORMAT_NAME,
        "files": [_file_to_dict(f) for f in files],
    }


def _file_to_dict(f):
    return {
        "old_path": f.old_path,
        "new_path": f.new_path,
        "hunks": [_hunk_to_dict(h) for h in f.hunks],
    }


def _hunk_to_dict(h):
    return {
        "old_start": h.old_start,
        "old_count": h.old_count,
        "new_start": h.new_start,
        "new_count": h.new_count,
        "section": h.section,
        "lines": [{"type": line.kind, "text": line.text} for line in h.lines],
    }


def dumps(files, indent=2):
    return json.dumps(to_json_doc(files), indent=indent)


def from_json_doc(doc):
    files = []
    for f in doc.get("files", []):
        hunks = []
        for h in f.get("hunks", []):
            lines = [DiffLine(l["type"], l["text"]) for l in h["lines"]]
            hunks.append(Hunk(
                h["old_start"], h["old_count"],
                h["new_start"], h["new_count"],
                h.get("section", ""), lines,
            ))
        files.append(FileDiff(f["old_path"], f["new_path"], hunks))
    return files


def loads(text):
    return from_json_doc(json.loads(text))


def to_unified_diff(files):
    out = []
    for f in files:
        out.append(f"--- {f.old_path}")
        out.append(f"+++ {f.new_path}")
        for h in f.hunks:
            header = f"@@ -{h.old_start},{h.old_count} +{h.new_start},{h.new_count} @@"
            if h.section:
                header += f" {h.section}"
            out.append(header)
            for line in h.lines:
                if line.kind == "marker":
                    out.append(f"\\{line.text}")
                else:
                    out.append(_KIND_TO_PREFIX[line.kind] + line.text)
    return "\n".join(out) + "\n"
