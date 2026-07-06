"""Small CODEOWNERS parser for MVP routing."""

from __future__ import annotations

import fnmatch
from pathlib import Path


CodeownersRule = tuple[str, list[str]]


def parse_codeowners(text: str) -> list[CodeownersRule]:
    rules: list[CodeownersRule] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        rules.append((parts[0], parts[1:]))
    return rules


def load_codeowners(paths: list[str], repo_root: str | Path = ".") -> list[CodeownersRule]:
    root = Path(repo_root)
    for path in paths:
        candidate = root / path
        if candidate.exists():
            return parse_codeowners(candidate.read_text(encoding="utf-8"))
    return []


def owners_for_files(files: list[str], rules: list[CodeownersRule]) -> dict[str, list[str]]:
    return {file_path: owners_for_file(file_path, rules) for file_path in files}


def owners_for_file(file_path: str, rules: list[CodeownersRule]) -> list[str]:
    owners: list[str] = []
    normalized = file_path.replace("\\", "/").lstrip("/")
    for pattern, pattern_owners in rules:
        if _matches(pattern, normalized):
            owners = pattern_owners
    return owners


def _matches(pattern: str, file_path: str) -> bool:
    normalized = pattern.replace("\\", "/").lstrip("/")
    if normalized == "*":
        return True
    if normalized.endswith("/"):
        return file_path.startswith(normalized)
    if normalized.endswith("/**"):
        return file_path.startswith(normalized[:-3].rstrip("/") + "/")
    if "/" not in normalized:
        return fnmatch.fnmatch(Path(file_path).name, normalized)
    return fnmatch.fnmatch(file_path, normalized)
