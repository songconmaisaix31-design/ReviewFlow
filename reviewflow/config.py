"""Configuration loading for ReviewFlow AI."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "review": {
        "dry_run": True,
        "max_context_chars": 180_000,
        "include_repository_guidance": True,
    },
    "blocking": {
        "fail_on_p0": True,
        "fail_on_p1": False,
        "fail_on_quality_gate_failed": False,
        "fail_on_critical_dependency": True,
    },
    "codex": {
        "enabled": True,
        "command_env": "REVIEWFLOW_CODEX_COMMAND",
        "timeout_seconds": 180,
        "prompt_path": "prompts/codex_review.md",
        "auto_push_patch": False,
        "offline_stub_when_missing": True,
    },
    "sonarqube": {"enabled": False},
    "dependency": {
        "enabled": True,
        "manifest_patterns": [
            "package.json",
            "package-lock.json",
            "pnpm-lock.yaml",
            "yarn.lock",
            "requirements.txt",
            "pyproject.toml",
            "poetry.lock",
            "go.mod",
            "go.sum",
            "pom.xml",
        ],
    },
    "owners": {
        "enabled": True,
        "codeowners_paths": [".github/CODEOWNERS", "CODEOWNERS", "examples/CODEOWNERS.example"],
        "require_code_owner_review": True,
    },
    "report": {
        "output_json": "review-report.json",
        "output_markdown": "review-summary.md",
        "output_context": "review-context.json",
    },
    "github": {
        "enabled": True,
        "dry_run": True,
        "token_env": "GITHUB_TOKEN",
        "request_reviewers": False,
        "comment_on_pr": False,
    },
}


def load_config(path: str | Path | None) -> dict[str, Any]:
    config = deepcopy(DEFAULT_CONFIG)
    if not path:
        return config

    data_path = Path(path)
    if not data_path.exists():
        raise FileNotFoundError(f"Config file not found: {data_path}")

    loaded = _load_structured_file(data_path)
    if not isinstance(loaded, dict):
        raise ValueError("Config root must be an object")
    return _deep_merge(config, loaded)


def _load_structured_file(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)

    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except ModuleNotFoundError:
        return _parse_simple_yaml(text)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]
        if content.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError("Invalid YAML list placement")
            parent.append(_coerce_scalar(content[2:].strip()))
            continue

        key, sep, value = content.partition(":")
        if not sep:
            raise ValueError(f"Invalid YAML line: {raw_line}")
        key = key.strip()
        value = value.strip()

        if value:
            parent[key] = _coerce_scalar(value)
            continue

        child: dict[str, Any] | list[Any]
        next_is_list = _next_content_is_list(text.splitlines(), raw_line)
        child = [] if next_is_list else {}
        parent[key] = child
        stack.append((indent, child))

    return root


def _next_content_is_list(lines: list[str], current: str) -> bool:
    try:
        index = lines.index(current)
    except ValueError:
        return False
    current_indent = len(current) - len(current.lstrip(" "))
    for next_line in lines[index + 1 :]:
        stripped = next_line.split("#", 1)[0].strip()
        if not stripped:
            continue
        next_indent = len(next_line) - len(next_line.lstrip(" "))
        return next_indent > current_indent and stripped.startswith("- ")
    return False


def _coerce_scalar(value: str) -> Any:
    value = value.strip().strip('"').strip("'")
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value
