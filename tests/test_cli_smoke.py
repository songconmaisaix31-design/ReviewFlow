import json
from pathlib import Path

from reviewflow.cli import main


def test_cli_smoke_generates_artifacts(tmp_path: Path) -> None:
    exit_code = main(
        [
            "run",
            "--event-path",
            "examples/github_pull_request_event.json",
            "--diff-path",
            "examples/sample_pr_diff.patch",
            "--config",
            "reviewflow.config.example.yml",
            "--output-dir",
            str(tmp_path),
            "--dry-run",
        ]
    )

    assert exit_code == 0
    report_path = tmp_path / "review-report.json"
    summary_path = tmp_path / "review-summary.md"
    context_path = tmp_path / "review-context.json"
    assert report_path.exists()
    assert summary_path.exists()
    assert context_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["risk_level"] == "HIGH"
    assert report["status"] == "WARNING"
    assert "src/orders/refund.py" in report["changed_files"]
