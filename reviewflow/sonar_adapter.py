"""SonarQube sample result normalization."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


EMPTY_SONAR_SUMMARY = {
    "enabled": False,
    "quality_gate": "UNKNOWN",
    "bugs": 0,
    "vulnerabilities": 0,
    "code_smells": 0,
    "coverage_on_new_code": None,
    "issues": [],
}


def load_sonar_summary(config: dict[str, Any]) -> dict[str, Any]:
    sonar_config = config.get("sonarqube", {})
    if not sonar_config.get("enabled", False):
        return dict(EMPTY_SONAR_SUMMARY)

    input_path = os.environ.get("REVIEWFLOW_SONAR_INPUT") or sonar_config.get("input_path")
    if not input_path or not Path(input_path).exists():
        summary = dict(EMPTY_SONAR_SUMMARY)
        summary["enabled"] = True
        return summary

    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
    issues = payload.get("issues", [])
    return {
        "enabled": True,
        "quality_gate": payload.get("qualityGate", "UNKNOWN"),
        "bugs": int(payload.get("newBugs", 0)),
        "vulnerabilities": int(payload.get("newVulnerabilities", 0)),
        "code_smells": int(payload.get("newCodeSmells", 0)),
        "coverage_on_new_code": payload.get("coverageOnNewCode"),
        "duplicated_lines_density": payload.get("duplicatedLinesDensity"),
        "issues": issues if isinstance(issues, list) else [],
    }


def sonar_findings(summary: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for index, issue in enumerate(summary.get("issues", []), start=1):
        findings.append(
            {
                "id": f"SONAR-{index:03d}",
                "severity": "P1" if issue.get("type") == "VULNERABILITY" else "P2",
                "category": "security" if issue.get("type") == "VULNERABILITY" else "quality",
                "file": issue.get("component", ""),
                "line": issue.get("line"),
                "title": issue.get("message", "SonarQube issue"),
                "evidence": f"SonarQube reported {issue.get('severity', 'UNKNOWN')} {issue.get('type', 'ISSUE')}.",
                "recommendation": "Review and resolve the reported SonarQube issue before merge.",
                "confidence": "medium",
                "source": "sonar",
            }
        )
    return findings
