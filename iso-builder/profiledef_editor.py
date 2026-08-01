"""Structured parser/writer for an archiso profiledef.sh.

profiledef.sh has a small, fixed set of fields (unlike pacman.conf, which
is a heavily-commented reference file worth preserving byte-for-byte).
This does a full, canonical rewrite instead of minimal-diff patching --
much simpler, and safe here since these profiledef.sh files don't carry
hand-written commentary beyond the shebang/shellcheck header, which IS
preserved.
"""

from __future__ import annotations

import re
import shlex

SCALAR_FIELDS = [
    "iso_name", "iso_label", "iso_publisher", "iso_application",
    "iso_version", "install_dir", "arch", "pacman_conf", "airootfs_image_type",
]
ARRAY_FIELDS = ["bootmodes", "airootfs_image_tool_options"]

_HEADER_RE = re.compile(r"^#.*$")
_SCALAR_RE = re.compile(r"^(\w+)=(.*)$")
_ARRAY_RE = re.compile(r"^(\w+)=\((.*)\)\s*$")
_PERM_ENTRY_RE = re.compile(r'^\s*\["([^"]+)"\]="([^"]*)"\s*$')


def parse_profiledef(text):
    """Returns {"header": [lines], "scalars": {name: value}, "arrays":
    {name: [items]}, "permissions": [(path, spec), ...]}.
    """
    lines = text.splitlines()

    header = []
    for line in lines:
        if line.startswith("#!") or line.startswith("#"):
            header.append(line)
        else:
            break

    scalars = {}
    arrays = {}
    permissions = []
    in_perm_block = False

    for line in lines:
        if in_perm_block:
            if line.strip() == ")":
                in_perm_block = False
                continue
            m = _PERM_ENTRY_RE.match(line)
            if m:
                permissions.append((m.group(1), m.group(2)))
            continue

        if line.strip() == "file_permissions=(":
            in_perm_block = True
            continue

        m = _ARRAY_RE.match(line)
        if m and m.group(1) in ARRAY_FIELDS:
            arrays[m.group(1)] = shlex.split(m.group(2))
            continue

        m = _SCALAR_RE.match(line)
        if m and m.group(1) in SCALAR_FIELDS:
            raw = m.group(2)
            if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
                scalars[m.group(1)] = raw[1:-1]
            else:
                scalars[m.group(1)] = raw

    return {
        "header": header or ["#!/usr/bin/env bash", "# shellcheck disable=SC2034"],
        "scalars": scalars,
        "arrays": arrays,
        "permissions": permissions,
    }


def _scalar_line(data, name):
    return f'{name}="{data["scalars"][name]}"' if name in data["scalars"] else None


def _array_line(data, name):
    if name not in data["arrays"]:
        return None
    items = " ".join(f"'{item}'" for item in data["arrays"][name])
    return f"{name}=({items})"


def render_profiledef(data):
    # Field order matches archiso's own profiledef.sh convention: identity
    # scalars, then bootmodes, then arch/pacman_conf/image-type scalars,
    # then the image tool options array, then file_permissions.
    lines = list(data["header"])
    lines.append("")

    for name in ["iso_name", "iso_label", "iso_publisher", "iso_application", "iso_version", "install_dir"]:
        line = _scalar_line(data, name)
        if line is not None:
            lines.append(line)

    line = _array_line(data, "bootmodes")
    if line is not None:
        lines.append(line)

    for name in ["arch", "pacman_conf", "airootfs_image_type"]:
        line = _scalar_line(data, name)
        if line is not None:
            lines.append(line)

    line = _array_line(data, "airootfs_image_tool_options")
    if line is not None:
        lines.append(line)

    if data["permissions"]:
        lines.append("file_permissions=(")
        for path, spec in data["permissions"]:
            lines.append(f'  ["{path}"]="{spec}"')
        lines.append(")")

    return "\n".join(lines) + "\n"
