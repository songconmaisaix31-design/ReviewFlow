"""Unified diff parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


HUNK_RE = re.compile(r"^@@ -(?P<old_start>\d+)(?:,\d+)? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@")


@dataclass(frozen=True)
class ChangedFile:
    path: str
    old_path: str | None
    status: str
    added_ranges: list[tuple[int, int]] = field(default_factory=list)
    patch: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "old_path": self.old_path,
            "status": self.status,
            "added_ranges": [[start, end] for start, end in self.added_ranges],
            "patch": self.patch,
        }


def collect_diff(diff_path: str | Path) -> dict[str, object]:
    diff_text = Path(diff_path).read_text(encoding="utf-8")
    files = parse_unified_diff(diff_text)
    return {
        "raw_diff": diff_text,
        "changed_files": [file.to_dict() for file in files],
        "changed_file_paths": [file.path for file in files],
    }


def parse_unified_diff(diff_text: str) -> list[ChangedFile]:
    files: list[ChangedFile] = []
    current_lines: list[str] = []
    current_old: str | None = None
    current_new: str | None = None

    def flush() -> None:
        nonlocal current_lines, current_old, current_new
        if current_new is None:
            current_lines = []
            return
        patch = "\n".join(current_lines).rstrip() + "\n"
        files.append(_build_changed_file(current_old, current_new, patch))
        current_lines = []
        current_old = None
        current_new = None

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            flush()
            current_lines = [line]
            parts = line.split()
            current_old = _strip_git_prefix(parts[2]) if len(parts) > 2 else None
            current_new = _strip_git_prefix(parts[3]) if len(parts) > 3 else None
            continue
        if current_lines:
            current_lines.append(line)
            if line.startswith("--- "):
                value = line[4:].strip()
                current_old = None if value == "/dev/null" else _strip_git_prefix(value)
            elif line.startswith("+++ "):
                value = line[4:].strip()
                current_new = None if value == "/dev/null" else _strip_git_prefix(value)
    flush()
    return files


def _build_changed_file(old_path: str | None, new_path: str | None, patch: str) -> ChangedFile:
    if new_path is None and old_path is None:
        raise ValueError("Diff file entry has no path")
    path = new_path or old_path or ""
    status = "modified"
    if old_path is None:
        status = "added"
    elif new_path is None:
        status = "deleted"
    elif old_path != new_path:
        status = "renamed"

    return ChangedFile(
        path=path,
        old_path=old_path,
        status=status,
        added_ranges=_extract_added_ranges(patch),
        patch=patch,
    )


def _extract_added_ranges(patch: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    new_line = 0
    active_start: int | None = None
    active_end: int | None = None

    def close_range() -> None:
        nonlocal active_start, active_end
        if active_start is not None and active_end is not None:
            ranges.append((active_start, active_end))
        active_start = None
        active_end = None

    for line in patch.splitlines():
        match = HUNK_RE.match(line)
        if match:
            close_range()
            new_line = int(match.group("new_start"))
            continue
        if line.startswith(("+++", "---", "diff --git")):
            continue
        if line.startswith("+"):
            if active_start is None:
                active_start = new_line
            active_end = new_line
            new_line += 1
        elif line.startswith("-"):
            close_range()
        else:
            close_range()
            if new_line:
                new_line += 1
    close_range()
    return ranges


def _strip_git_prefix(value: str) -> str:
    value = value.strip()
    if value.startswith("a/") or value.startswith("b/"):
        return value[2:]
    return value
