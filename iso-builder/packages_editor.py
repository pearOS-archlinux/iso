"""Line-based parser/writer for pear/airootfs/etc/packages.x86_64.

The file is mostly one package name per line. A package can be disabled by
commenting the whole line out (e.g. "#electron"). A handful of lines are
plain comments/section headers (e.g. "# pearOS Apps") rather than disabled
packages -- distinguished heuristically: a commented line whose body is a
single bare package-name token is treated as a toggleable package; anything
else (spaces, multiple words) is treated as an inert comment and passed
through unchanged.
"""

from __future__ import annotations

import re

_PKG_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")


def parse_packages(text):
    """Returns a list of entries, one per line, in file order.

    entry kinds:
      {"kind": "package", "name": str, "enabled": bool}
      {"kind": "other", "raw": str}   -- comments, section headers, blanks
    """
    entries = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            entries.append({"kind": "other", "raw": raw_line})
            continue
        if stripped.startswith("#"):
            body = stripped[1:].strip()
            if _PKG_TOKEN_RE.match(body):
                entries.append({"kind": "package", "name": body, "enabled": False})
                continue
            entries.append({"kind": "other", "raw": raw_line})
            continue
        if _PKG_TOKEN_RE.match(stripped):
            entries.append({"kind": "package", "name": stripped, "enabled": True})
            continue
        entries.append({"kind": "other", "raw": raw_line})
    return entries


def render_packages(entries):
    lines = []
    for entry in entries:
        if entry["kind"] == "package":
            lines.append(entry["name"] if entry["enabled"] else f"#{entry['name']}")
        else:
            lines.append(entry["raw"])
    return "\n".join(lines) + "\n"
