import json

from reviewflow.delivery_audit import audit_repository, sync_content_candidate, write_delivery_audit_artifacts


def test_delivery_audit_generates_safe_client_artifacts(tmp_path):
    repo = tmp_path / "client-app"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "docs").mkdir()
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname = 'client-app'\n", encoding="utf-8")
    (repo / "src" / "app.py").write_text("print('ready')\n", encoding="utf-8")
    (repo / "tests" / "test_app.py").write_text("def test_app(): assert True\n", encoding="utf-8")
    (repo / "README.md").write_text("# Client App\n", encoding="utf-8")
    (repo / "docs" / "acceptance.md").write_text("Passed locally.\n", encoding="utf-8")
    (repo / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    (repo / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
    (repo / ".env").write_text("API_KEY=must-not-appear\n", encoding="utf-8")
    evidence = tmp_path / "evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "claim": "The main workflow passed acceptance.",
                        "evidence_paths": ["docs/acceptance.md"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = audit_repository(repo, evidence)
    paths = write_delivery_audit_artifacts(report, tmp_path / "output")

    assert report["overall_status"] == "READY_FOR_ACCEPTANCE"
    assert report["evidence_score"] == 100
    assert all(".env" not in path for item in report["dimensions"] for path in item["evidence"])
    assert {
        "json",
        "markdown",
        "html",
        "content_brief",
        "content_candidates_json",
        "content_candidates_markdown",
        "wiki_capsule",
    } == set(paths)
    assert "must-not-appear" not in paths["html"].read_text(encoding="utf-8")
    assert "Cheat on Content" in paths["content_brief"].read_text(encoding="utf-8")
    candidates = json.loads(paths["content_candidates_json"].read_text(encoding="utf-8"))["candidates"]
    assert len(candidates[0]["id"]) == 12
    assert candidates[0]["source"] == "audit:reviewflow"
    assert "client-app" not in candidates[0]["snapshot_text"]

    content_project = tmp_path / "content-project"
    content_project.mkdir()
    (content_project / ".cheat-state.json").write_text("{}\n", encoding="utf-8")
    assert sync_content_candidate(report, content_project) is True
    assert sync_content_candidate(report, content_project) is False
    assert (content_project / "candidates.md").read_text(encoding="utf-8").count(candidates[0]["id"]) == 1
