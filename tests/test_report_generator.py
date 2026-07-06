from reviewflow.report_generator import build_report, render_markdown_report, should_fail


def test_report_generator_orders_findings_and_sets_risk() -> None:
    report = build_report(
        context={
            "changed_files": [{"path": "src/app.py"}],
            "owner_mapping": {"src/app.py": ["@team"]},
            "sonar_summary": {},
            "dependency_summary": {},
        },
        codex_result={
            "summary": "done",
            "findings": [
                {
                    "id": "LOW",
                    "severity": "P3",
                    "category": "quality",
                    "file": "src/app.py",
                    "title": "Minor issue",
                    "evidence": "e",
                    "recommendation": "r",
                    "confidence": "medium",
                    "source": "codex",
                },
                {
                    "id": "HIGH",
                    "severity": "P1",
                    "category": "security",
                    "file": "src/app.py",
                    "title": "High issue",
                    "evidence": "e",
                    "recommendation": "r",
                    "confidence": "high",
                    "source": "codex",
                },
            ],
        },
        sonar_findings=[],
        dependency_findings=[],
    )

    assert report["risk_level"] == "HIGH"
    assert report["status"] == "WARNING"
    assert [finding["id"] for finding in report["findings"]] == ["HIGH", "LOW"]
    assert not should_fail(report, {"blocking": {"fail_on_p0": True, "fail_on_p1": False}})
    assert should_fail(report, {"blocking": {"fail_on_p1": True}})
    assert "# ReviewFlow AI Summary" in render_markdown_report(report)
