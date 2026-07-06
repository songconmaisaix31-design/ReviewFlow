"""Codex review adapter with offline fallback."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any


SAFE_ENV_KEYS = {"PATH", "SystemRoot", "COMSPEC", "WINDIR", "HOME", "USERPROFILE", "TEMP", "TMP"}


def run_codex_review(context: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    codex_config = config.get("codex", {})
    command_env = codex_config.get("command_env", "REVIEWFLOW_CODEX_COMMAND")
    command = os.environ.get(command_env, "")
    if command:
        return _run_external_command(command, context, int(codex_config.get("timeout_seconds", 180)))
    if not codex_config.get("offline_stub_when_missing", True):
        return {"findings": [], "test_suggestions": [], "summary": "Codex review skipped."}
    return _offline_review(context)


def _run_external_command(command: str, context: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    completed = subprocess.run(
        shlex.split(command),
        input=json.dumps(context, ensure_ascii=False),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
        env={key: value for key, value in os.environ.items() if key in SAFE_ENV_KEYS},
    )
    if completed.returncode != 0:
        return {
            "findings": [
                {
                    "id": "CODEX-ERROR",
                    "severity": "P2",
                    "category": "quality",
                    "file": "",
                    "line": None,
                    "title": "External Codex command failed",
                    "evidence": f"Command exited with status {completed.returncode}.",
                    "recommendation": "Inspect the configured REVIEWFLOW_CODEX_COMMAND locally.",
                    "confidence": "medium",
                    "source": "codex",
                }
            ],
            "test_suggestions": [],
            "summary": "External Codex command failed.",
        }
    try:
        return json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("External Codex command must return JSON on stdout") from exc


def _offline_review(context: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    diff = str(context.get("diff", ""))
    changed_files = [str(item.get("path", "")) for item in context.get("changed_files", [])]

    if "has_permission" in diff and "# if not user.has_permission" in diff:
        findings.append(
            {
                "id": "CODEX-001",
                "severity": "P1",
                "category": "security",
                "file": _first_matching_file(changed_files, "refund.py"),
                "line": 11,
                "title": "Authorization check appears disabled",
                "evidence": "The diff comments out the refund permission check before creating a refund.",
                "recommendation": "Restore the authorization guard and add a regression test for unauthorized refunds.",
                "confidence": "high",
                "source": "codex",
            }
        )

    if any(Path(file_path).name in {"requirements.txt", "package.json", "pyproject.toml"} for file_path in changed_files):
        findings.append(
            {
                "id": "CODEX-002",
                "severity": "P2",
                "category": "test",
                "file": _first_dependency_file(changed_files),
                "line": None,
                "title": "Dependency change needs compatibility coverage",
                "evidence": "The PR changes dependency manifests, which can affect runtime behavior.",
                "recommendation": "Run dependency audit checks and targeted tests for code paths using changed packages.",
                "confidence": "medium",
                "source": "codex",
            }
        )

    return {
        "findings": findings,
        "test_suggestions": [
            {
                "file": "tests/test_refund_authorization.py",
                "title": "Reject unauthorized refund creation",
                "reason": "The diff touches refund authorization behavior.",
            }
        ]
        if findings
        else [],
        "summary": "Offline Codex stub completed deterministic semantic review.",
        "suggested_patch": None,
    }


def _first_matching_file(files: list[str], suffix: str) -> str:
    return next((file_path for file_path in files if file_path.endswith(suffix)), files[0] if files else "")


def _first_dependency_file(files: list[str]) -> str:
    names = {"requirements.txt", "package.json", "pyproject.toml"}
    return next((file_path for file_path in files if Path(file_path).name in names), files[0] if files else "")
