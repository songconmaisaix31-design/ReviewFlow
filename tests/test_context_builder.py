from reviewflow.context_builder import build_review_context


def test_build_review_context_enforces_limit() -> None:
    context = build_review_context(
        event={"pull_request": {"number": 7, "title": "Demo"}},
        diff_data={
            "raw_diff": "x" * 500,
            "changed_files": [{"path": "src/app.py"}],
        },
        owner_mapping={"src/app.py": ["@team"]},
        sonar_summary={"quality_gate": "PASSED"},
        dependency_summary={"alerts": []},
        config={"review": {"max_context_chars": 300, "include_repository_guidance": False}},
    )

    assert context["pull_request"]["number"] == 7
    assert context["owner_mapping"] == {"src/app.py": ["@team"]}
    assert len(str(context)) <= 350
