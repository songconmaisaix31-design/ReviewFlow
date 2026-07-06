"""Dependency change and alert normalization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST_PATTERNS = {
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
}


def load_dependency_summary(config: dict[str, Any], changed_files: list[str]) -> dict[str, Any]:
    dependency_config = config.get("dependency", {})
    patterns = set(dependency_config.get("manifest_patterns") or DEFAULT_MANIFEST_PATTERNS)
    manifest_changes = [
        file_path
        for file_path in changed_files
        if Path(file_path).name in patterns or file_path in patterns
    ]

    alerts = []
    alert_path = dependency_config.get("alert_input_path")
    if dependency_config.get("enabled", True) and alert_path and Path(alert_path).exists():
        payload = json.loads(Path(alert_path).read_text(encoding="utf-8"))
        alerts = payload.get("alerts", []) if isinstance(payload.get("alerts", []), list) else []

    normalized_alerts = [_normalize_alert(alert) for alert in alerts]
    return {
        "enabled": bool(dependency_config.get("enabled", True)),
        "manifest_changes": manifest_changes,
        "alerts": normalized_alerts,
        "highest_severity": _highest_severity(normalized_alerts),
    }


def dependency_findings(summary: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for index, alert in enumerate(summary.get("alerts", []), start=1):
        severity = str(alert.get("severity", "low")).lower()
        findings.append(
            {
                "id": f"DEP-{index:03d}",
                "severity": "P0" if severity == "critical" else "P1" if severity == "high" else "P2",
                "category": "dependency",
                "file": alert.get("manifest", ""),
                "line": None,
                "title": f"Dependency risk in {alert.get('package', 'unknown package')}",
                "evidence": alert.get("summary", f"{severity} dependency alert"),
                "recommendation": _dependency_recommendation(alert),
                "confidence": "medium",
                "source": "dependency",
            }
        )
    return findings


def _normalize_alert(alert: dict[str, Any]) -> dict[str, Any]:
    return {
        "package": alert.get("package") or alert.get("dependency", {}).get("package", {}).get("name"),
        "manifest": alert.get("manifest") or alert.get("dependency", {}).get("manifest_path"),
        "severity": str(alert.get("severity") or alert.get("security_advisory", {}).get("severity") or "unknown").lower(),
        "vulnerable_range": alert.get("vulnerable_range"),
        "fixed_version": alert.get("fixed_version"),
        "summary": alert.get("summary") or alert.get("security_advisory", {}).get("summary", ""),
    }


def _dependency_recommendation(alert: dict[str, Any]) -> str:
    fixed = alert.get("fixed_version")
    if fixed:
        return f"Upgrade {alert.get('package', 'the package')} to {fixed} or later."
    return "Review the advisory and update or remove the affected dependency."


def _highest_severity(alerts: list[dict[str, Any]]) -> str:
    order = {"unknown": 0, "low": 1, "medium": 2, "moderate": 2, "high": 3, "critical": 4}
    highest = "unknown"
    for alert in alerts:
        severity = str(alert.get("severity", "unknown")).lower()
        if order.get(severity, 0) > order.get(highest, 0):
            highest = severity
    return highest
