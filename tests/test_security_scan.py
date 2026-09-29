import json

from reviewflow.cli import main
from reviewflow.security_scan import scan_repository, scan_should_fail, write_security_scan_artifacts


def test_security_scan_finds_built_in_and_redacted_sarif_issues(tmp_path):
    repo = tmp_path / "unsafe-app"
    workflow = repo / ".github" / "workflows"
    workflow.mkdir(parents=True)
    (repo / "app.py").write_text(
        """import hashlib
import pickle
import requests
import ssl
import subprocess
import tempfile
import yaml
from os import system as run_shell

def unsafe(user, items=[]):
    eval(user)
    run_shell(user)
    subprocess.run(user, shell=True)
    requests.get(user, verify=False)
    yaml.load(user)
    pickle.loads(user)
    tempfile.mktemp()
    hashlib.md5(user.encode())
    cursor.execute(f"SELECT * FROM users WHERE name = '{user}'")
    ssl._create_unverified_context()
    try:
        return items
    except:
        return []
""",
        encoding="utf-8",
    )
    (repo / "broken.py").write_text("def broken(:\n", encoding="utf-8")
    (workflow / "scan.yml").write_text(
        """on:
  pull_request_target:
permissions: write-all
  pull-requests: write
jobs:
  scan:
    steps:
      - uses: actions/checkout@v4
""",
        encoding="utf-8",
    )
    sarif = tmp_path / "external.sarif"
    result = {
        "ruleId": "secret-rule",
        "level": "error",
        "properties": {"security-severity": "9.1"},
        "message": {"text": "API_KEY=must-not-leak"},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": "../../private/secret.py"},
                    "region": {"startLine": 7},
                }
            }
        ],
    }
    sarif.write_text(
        json.dumps(
            {
                "version": "2.1.0",
                "runs": [
                    {
                        "tool": {"driver": {"name": "unsafe scanner name"}},
                        "results": [result, result],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = scan_repository(repo, sarif_paths=[sarif])
    rule_ids = {finding["rule_id"] for finding in report["findings"]}

    assert {
        "RF-PY000",
        "RF-PY001",
        "RF-PY002",
        "RF-PY003",
        "RF-PY004",
        "RF-PY005",
        "RF-PY006",
        "RF-PY007",
        "RF-PY008",
        "RF-PY009",
        "RF-PY010",
        "RF-PY011",
        "RF-PY013",
        "RF-PY014",
        "RF-GH001",
        "RF-GH002",
        "RF-GH003",
        "RF-GH004",
        "secret-rule",
    } <= rule_ids
    assert sum(finding["rule_id"] == "secret-rule" for finding in report["findings"]) == 1
    external = next(finding for finding in report["findings"] if finding["rule_id"] == "secret-rule")
    assert external["file"] == "<external>"
    assert "must-not-leak" not in json.dumps(report)
    assert scan_should_fail(report, "P1") is True
    assert scan_should_fail(report, "none") is False

    paths = write_security_scan_artifacts(report, tmp_path / "artifacts")
    assert {"json", "markdown", "sarif"} == set(paths)
    assert all("must-not-leak" not in path.read_text(encoding="utf-8") for path in paths.values())

    cli_output = tmp_path / "cli-output"
    assert main(["scan", "--repo-path", str(repo), "--output-dir", str(cli_output), "--fail-on", "none"]) == 0
    assert (cli_output / "security-scan.sarif").is_file()
