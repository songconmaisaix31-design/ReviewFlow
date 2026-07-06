"""Report normalization and rendering."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SEVERITY_ORDER = {"P0": 4, "P1": 3, "P2": 2, "P3": 1}


def build_report(
    *,
    context: dict[str, Any],
    codex_result: dict[str, Any],
    sonar_findings: list[dict[str, Any]],
    dependency_findings: list[dict[str, Any]],
) -> dict[str, Any]:
    findings = _normalize_findings(
        list(codex_result.get("findings", [])) + sonar_findings + dependency_findings
    )
    risk_level = _risk_level(findings)
    status = "FAILED" if any(item["severity"] == "P0" for item in findings) else "WARNING" if findings else "PASSED"
    return {
        "risk_level": risk_level,
        "status": status,
        "summary": codex_result.get("summary", "ReviewFlow AI completed review."),
        "changed_files": [item.get("path", "") for item in context.get("changed_files", [])],
        "owner_mapping": context.get("owner_mapping", {}),
        "sonar_summary": context.get("sonar_summary", {}),
        "dependency_summary": context.get("dependency_summary", {}),
        "findings": findings,
        "test_suggestions": list(codex_result.get("test_suggestions", [])),
        "suggested_patch": codex_result.get("suggested_patch"),
        "human_review_required": bool(findings or context.get("owner_mapping")),
    }


def write_report_artifacts(report: dict[str, Any], output_dir: str | Path, config: dict[str, Any]) -> dict[str, Path]:
    validate_report(report)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    report_config = config.get("report", {})
    json_path = output / report_config.get("output_json", "review-report.json")
    markdown_path = output / report_config.get("output_markdown", "review-summary.md")
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown_report(report), encoding="utf-8")
    paths = {"json": json_path, "markdown": markdown_path}
    suggested_patch = report.get("suggested_patch")
    if suggested_patch:
        patch_path = output / "review-patch.diff"
        patch_path.write_text(str(suggested_patch), encoding="utf-8")
        paths["patch"] = patch_path
    return paths


def render_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# ReviewFlow AI Summary",
        "",
        f"- Status: {report['status']}",
        f"- Risk level: {report['risk_level']}",
        f"- Human review required: {str(report['human_review_required']).lower()}",
        "",
        "## Changed Files",
    ]
    lines.extend(f"- `{file_path}`" for file_path in report.get("changed_files", []))
    lines.extend(["", "## Findings"])
    findings = report.get("findings", [])
    if not findings:
        lines.append("- No findings.")
    for finding in findings:
        location = finding["file"]
        if finding.get("line"):
            location = f"{location}:{finding['line']}"
        lines.extend(
            [
                f"### {finding['id']} {finding['severity']} - {finding['title']}",
                f"- Category: {finding['category']}",
                f"- Source: {finding['source']}",
                f"- Location: `{location}`",
                f"- Evidence: {finding['evidence']}",
                f"- Recommendation: {finding['recommendation']}",
                "",
            ]
        )
    lines.extend(["## Test Suggestions"])
    suggestions = report.get("test_suggestions", [])
    if not suggestions:
        lines.append("- No additional test suggestions.")
    for suggestion in suggestions:
        lines.append(f"- `{suggestion['file']}`: {suggestion['title']} - {suggestion['reason']}")
    return "\n".join(lines).rstrip() + "\n"


def should_fail(report: dict[str, Any], config: dict[str, Any]) -> bool:
    blocking = config.get("blocking", {})
    severities = {finding.get("severity") for finding in report.get("findings", [])}
    if blocking.get("fail_on_p0", True) and "P0" in severities:
        return True
    if blocking.get("fail_on_p1", False) and "P1" in severities:
        return True
    if (
        blocking.get("fail_on_quality_gate_failed", False)
        and report.get("sonar_summary", {}).get("quality_gate") == "FAILED"
    ):
        return True
    if (
        blocking.get("fail_on_critical_dependency", True)
        and report.get("dependency_summary", {}).get("highest_severity") == "critical"
    ):
        return True
    return False


def validate_report(report: dict[str, Any], schema_path: str | Path = "schemas/review_report.schema.json") -> None:
    path = Path(schema_path)
    if path.exists():
        try:
            import jsonschema  # type: ignore

            schema = json.loads(path.read_text(encoding="utf-8"))
            jsonschema.validate(report, schema)
            return
        except ModuleNotFoundError:
            pass
    required = {
        "risk_level",
        "status",
        "summary",
        "changed_files",
        "owner_mapping",
        "sonar_summary",
        "dependency_summary",
        "findings",
        "test_suggestions",
        "human_review_required",
    }
    missing = sorted(required - set(report))
    if missing:
        raise ValueError(f"Report is missing required fields: {', '.join(missing)}")


def _normalize_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for index, finding in enumerate(findings, start=1):
        normalized.append(
            {
                "id": str(finding.get("id") or f"RF-{index:03d}"),
                "severity": finding.get("severity") if finding.get("severity") in SEVERITY_ORDER else "P3",
                "category": finding.get("category") or "quality",
                "file": str(finding.get("file") or ""),
                "line": finding.get("line"),
                "title": str(finding.get("title") or "Review finding"),
                "evidence": str(finding.get("evidence") or ""),
                "recommendation": str(finding.get("recommendation") or ""),
                "owner": finding.get("owner"),
                "confidence": finding.get("confidence") or "medium",
                "source": finding.get("source") or "rule",
            }
        )
    return sorted(normalized, key=lambda item: SEVERITY_ORDER[item["severity"]], reverse=True)


def _risk_level(findings: list[dict[str, Any]]) -> str:
    max_score = max((SEVERITY_ORDER.get(finding["severity"], 0) for finding in findings), default=0)
    if max_score >= 4:
        return "CRITICAL"
    if max_score == 3:
        return "HIGH"
    if max_score == 2:
        return "MEDIUM"
    return "LOW"
