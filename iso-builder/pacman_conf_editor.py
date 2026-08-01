"""Line-based parser/writer for repo blocks (with SigLevel) in a
pacman.conf-style file.

Each repo is `[name]` (or `#[name]` if disabled) followed by a SigLevel
line and a Server/Include line before the next section. Duplicate section
names are kept as separate entries in file order -- pear/pacman.conf
currently has duplicate [pearos]/[inled] blocks left over from an earlier
edit, and this editor is meant to make that visible/fixable rather than
silently merging them.

The [options] section is pacman's global settings, not a repo, and is
excluded from the parsed repo list.

render_repos() is written to be minimally invasive: a repo whose enabled
state and SigLevel weren't touched keeps its original line byte-for-byte
(spacing, alignment, everything). Only the leading '#' is added/removed
when a checkbox changes, and only the value is rewritten when SigLevel
text actually changes -- so running Save without editing anything produces
zero diff.
"""

from __future__ import annotations

import re

# No whitespace allowed between the hashes and '[': real (even disabled)
# section headers are always "[name]" or "#[name]" with nothing in between.
# pacman.conf's own documentation header uses an indented, commented
# example "#       [repo-name]" to explain the format -- that has to NOT
# match, or it shows up as a fake "repo-name" repo.
_SECTION_RE = re.compile(r"^(#*)\[([^\]]+)\]\s*$")
_SIGLEVEL_RE = re.compile(r"^(#*)(\s*SigLevel\s*=\s*)(.*)$")

COMMON_SIGLEVELS = [
    "Required DatabaseOptional",
    "PackageRequired",
    "Optional TrustAll",
    "Optional TrustedOnly",
    "Never",
]


def extract_global_siglevel(text, default="Required DatabaseOptional"):
    """The SigLevel set in [options] -- what a repo with no SigLevel line
    of its own actually inherits. Used to fill in real (non-empty) values
    for repos like core/extra/multilib that rely on that inheritance,
    rather than leaving them blank in the UI.
    """
    lines = text.splitlines()
    in_options = False
    for line in lines:
        stripped = line.strip()
        if stripped == "[options]":
            in_options = True
            continue
        if in_options and stripped.startswith("[") and stripped != "[options]":
            break
        if in_options:
            m = _SIGLEVEL_RE.match(line)
            if m and m.group(1) == "":
                return m.group(3).strip()
    return default


def parse_repos(text):
    """Returns a list of repo dicts, in file order, each with:
    name, header_line, enabled, siglevel_line (or None), siglevel_value,
    siglevel_enabled, block_end (line index, exclusive, where this repo's
    block ends -- the next section header).
    Internal (not for UI use): header_hashes, siglevel_hashes, siglevel_prefix
    -- original text needed to reproduce untouched lines byte-for-byte.
    """
    lines = text.splitlines()
    section_lines = []  # (line_idx, name, hashes)
    for i, line in enumerate(lines):
        m = _SECTION_RE.match(line)
        if m:
            hashes = m.group(1)
            name = m.group(2)
            section_lines.append((i, name, hashes))

    repos = []
    for idx, (line_idx, name, hashes) in enumerate(section_lines):
        next_line_idx = section_lines[idx + 1][0] if idx + 1 < len(section_lines) else len(lines)
        if name == "options":
            continue
        repo = {
            "name": name,
            "header_line": line_idx,
            "enabled": hashes == "",
            "header_hashes": hashes,
            "siglevel_line": None,
            "siglevel_value": "",
            "siglevel_enabled": False,
            "siglevel_hashes": "",
            "siglevel_prefix": "",
            "block_end": next_line_idx,
        }
        for j in range(line_idx + 1, next_line_idx):
            m2 = _SIGLEVEL_RE.match(lines[j])
            if m2:
                sig_hashes, sig_prefix, value = m2.groups()
                repo["siglevel_line"] = j
                repo["siglevel_value"] = value.strip()
                repo["siglevel_enabled"] = sig_hashes == ""
                repo["siglevel_hashes"] = sig_hashes
                repo["siglevel_prefix"] = sig_prefix
                break
        repos.append(repo)
    return repos


def new_repo(name, siglevel_value="", server=""):
    """A repo not yet in the file -- render_repos() inserts it before
    [core] (matching where build-binary itself splices in extra repos), or
    at the end of the file if there's no [core] section.
    """
    return {
        "name": name,
        "new": True,
        "enabled": True,
        "siglevel_value": siglevel_value,
        "server": server,
    }


def render_repos(text, repos):
    """Apply edits (enabled, siglevel_value, siglevel_enabled, delete) back
    into the original text. Lines that weren't actually changed are left
    byte-for-byte identical to the input. Entries created with new_repo()
    are inserted as brand new blocks.
    """
    lines = text.splitlines()
    existing = [r for r in repos if not r.get("new")]
    new_entries = [r for r in repos if r.get("new") and not r.get("delete")]

    for repo in sorted(existing, key=lambda r: r["header_line"], reverse=True):
        if repo.get("delete"):
            del lines[repo["header_line"]:repo["block_end"]]
            continue

        if repo["siglevel_line"] is not None:
            value_changed = repo["siglevel_value"] != _original_siglevel_value(lines, repo)
            enabled_changed = repo["siglevel_enabled"] != (repo["siglevel_hashes"] == "")
            if value_changed:
                prefix = "" if repo["siglevel_enabled"] else "#"
                lines[repo["siglevel_line"]] = f"{prefix}SigLevel = {repo['siglevel_value']}"
            elif enabled_changed:
                original = lines[repo["siglevel_line"]]
                lines[repo["siglevel_line"]] = _toggle_hash(
                    original, repo["siglevel_hashes"], repo["siglevel_enabled"]
                )
        elif repo["siglevel_value"]:
            lines.insert(repo["header_line"] + 1, f"SigLevel = {repo['siglevel_value']}")

        if repo["enabled"] != (repo["header_hashes"] == ""):
            original = lines[repo["header_line"]]
            lines[repo["header_line"]] = _toggle_hash(original, repo["header_hashes"], repo["enabled"])

    if new_entries:
        insert_at = next((i for i, line in enumerate(lines) if line.strip() == "[core]"), len(lines))
        block = []
        for repo in new_entries:
            prefix = "" if repo["enabled"] else "#"
            block.append(f"{prefix}[{repo['name']}]")
            if repo["siglevel_value"]:
                block.append(f"{prefix}SigLevel = {repo['siglevel_value']}")
            if repo["server"]:
                block.append(f"{prefix}Server = {repo['server']}")
            block.append("")
        lines[insert_at:insert_at] = block

    return "\n".join(lines) + "\n"


def _original_siglevel_value(lines, repo):
    m = _SIGLEVEL_RE.match(lines[repo["siglevel_line"]])
    return m.group(3).strip() if m else repo["siglevel_value"]


def _toggle_hash(original_line, original_hashes, want_enabled):
    """Add/remove exactly the leading '#' characters recorded at parse
    time, leaving the rest of the line (spacing, content) untouched.
    """
    if want_enabled:
        return original_line[len(original_hashes):]
    if original_hashes:
        return original_line  # already disabled
    return "#" + original_line
