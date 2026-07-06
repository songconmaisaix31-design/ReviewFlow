"""Review context assembly."""

from __future__ import annotations

from pathlib import Path
from typing import Any


GUIDANCE_FILES = ["AGENTS.md", "README.md"]


def build_review_context(
    *,
    event: dict[str, Any],
    diff_data: dict[str, Any],
    owner_mapping: dict[str, list[str]],
    sonar_summary: dict[str, Any],
    dependency_summary: dict[str, Any],
    config: dict[str, Any],
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    root = Path(repo_root)
    max_chars = int(config.get("review", {}).get("max_context_chars", 180_000))
    raw_diff = str(diff_data.get("raw_diff", ""))
    context = {
        "pull_request": _pull_request_summary(event),
        "changed_files": diff_data.get("changed_files", []),
        "owner_mapping": owner_mapping,
        "sonar_summary": sonar_summary,
        "dependency_summary": dependency_summary,
        "repository_guidance": _read_repository_guidance(root, config),
        "diff": _truncate(raw_diff, max_chars),
    }
    return _enforce_context_limit(context, max_chars)


def _pull_request_summary(event: dict[str, Any]) -> dict[str, Any]:
    pr = event.get("pull_request", {})
    return {
        "number": pr.get("number") or event.get("number"),
        "title": pr.get("title"),
        "author": (pr.get("user") or {}).get("login"),
        "url": pr.get("html_url"),
        "base_ref": (pr.get("base") or {}).get("ref"),
        "head_ref": (pr.get("head") or {}).get("ref"),
    }


def _read_repository_guidance(root: Path, config: dict[str, Any]) -> dict[str, str]:
    if not config.get("review", {}).get("include_repository_guidance", True):
        return {}
    guidance: dict[str, str] = {}
    for relative in GUIDANCE_FILES:
        path = root / relative
        if path.exists():
            guidance[relative] = _truncate(path.read_text(encoding="utf-8"), 12_000)
    return guidance


def _enforce_context_limit(context: dict[str, Any], max_chars: int) -> dict[str, Any]:
    serialized_length = len(str(context))
    if serialized_length <= max_chars:
        return context
    overflow = serialized_length - max_chars
    diff = str(context.get("diff", ""))
    context["diff"] = _truncate(diff, max(0, len(diff) - overflow - 500))
    return context


def _truncate(value: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(value) <= max_chars:
        return value
    return value[: max(0, max_chars - 40)] + "\n...[truncated by ReviewFlow AI]\n"
