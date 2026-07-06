# ReviewFlow AI Memory

## Architecture Decisions
- 2026-07-06: The MVP will be implemented as a Python package with a `python -m reviewflow.cli run` entry point.
- 2026-07-06: The first implementation will default to dry-run behavior and deterministic offline review output.
- 2026-07-06: The first implementation will avoid mandatory third-party runtime dependencies; tests may use `pytest`.
- 2026-07-06: The example config keeps `fail_on_p1` and `fail_on_quality_gate_failed` disabled so the bundled smoke demo can return exit code 0 while still producing HIGH/WARNING findings.

## Design Tradeoffs
- YAML support may be implemented as a small MVP parser if no YAML dependency is available.
- Real SonarQube, Dependabot, Codex, and GitHub API integrations are adapter boundaries, with local sample/offline behavior for the MVP.

## Known Issues
- No existing application code was present at project start.

## External Resources
- Source objective file: `C:\Users\DW\.codex\attachments\9e177ca9-5eec-41ac-a1a5-db71f65ac97c\goal-objective.md`
- Starter archive: `C:\Users\DW\Downloads\reviewflow_ai_starter.zip`

## Validation Record
- 2026-07-06: `python -m compileall reviewflow tests` passed.
- 2026-07-06: `python -m pytest` passed with 7 tests.
- 2026-07-06: `python -m reviewflow.cli run --event-path examples/github_pull_request_event.json --diff-path examples/sample_pr_diff.patch --config reviewflow.config.example.yml --output-dir .reviewflow --dry-run` passed and generated `.reviewflow/review-context.json`, `.reviewflow/review-report.json`, and `.reviewflow/review-summary.md`.
