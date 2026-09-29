# ReviewFlow AI Memory

## Architecture Decisions
- 2026-07-06: The MVP will be implemented as a Python package with a `python -m reviewflow.cli run` entry point.
- 2026-07-06: The first implementation will default to dry-run behavior and deterministic offline review output.
- 2026-07-06: The first implementation will avoid mandatory third-party runtime dependencies; tests may use `pytest`.
- 2026-07-06: The example config keeps `fail_on_p1` and `fail_on_quality_gate_failed` disabled so the bundled smoke demo can return exit code 0 while still producing HIGH/WARNING findings.
- 2026-07-07: The GitHub repository uses `main` as the remote default branch; the MVP implementation was merged from local `master` into local `main` with unrelated histories preserved.
- 2026-07-11: Delivery Audit is a deterministic local CLI mode for evidence-based AI application acceptance; it inventories safe file paths and never infers production acceptance from repository structure.
- 2026-07-11: Delivery Audit generates JSON, Chinese Markdown, Chinese HTML, and a source-free content brief that can enter the Cheat on Content blind-prediction and T+3 retrospective loop.
- 2026-07-11: The local fusion boundary exports Cheat-compatible candidate JSON/Markdown and a Wiki capsule; only `sync-content` writes outside the audit output, and only to an initialized local content project with ID-based deduplication.
- 2026-07-11: ReviewFlow never writes directly into the Personal Wiki. Wiki ingestion remains governed by the Wiki repository's evidence and promotion workflow.
- 2026-07-11: Repository Security Scan uses a built-in Python AST baseline plus safe SARIF aggregation. Specialist scanners remain separate producers; ReviewFlow never claims vulnerability absence from a clean local result.
- 2026-07-11: SARIF import intentionally discards external messages and snippets, bounds file/result size, sanitizes paths, and deduplicates rule/path/line findings.

## Design Tradeoffs
- YAML support may be implemented as a small MVP parser if no YAML dependency is available.
- Real SonarQube, Dependabot, Codex, and GitHub API integrations are adapter boundaries, with local sample/offline behavior for the MVP.
- Delivery Audit intentionally avoids a dashboard, database, account system, and external model dependency so a paid pilot can run locally within one week.

## Known Issues
- No existing application code was present at project start.

## External Resources
- Source objective file: `C:\Users\DW\.codex\attachments\9e177ca9-5eec-41ac-a1a5-db71f65ac97c\goal-objective.md`
- Starter archive: `C:\Users\DW\Downloads\reviewflow_ai_starter.zip`
- Content experiment workflow: `https://github.com/XBuilderLAB/cheat-on-content` (MIT; installed locally as a Codex skill on 2026-07-11).
- The first generic skill installation copied only root files. The installation was corrected with the project's own installer in frozen-copy mode and verified to include the main skill plus 15 sub-skills.

## Validation Record
- 2026-07-06: `python -m compileall reviewflow tests` passed.
- 2026-07-06: `python -m pytest` passed with 7 tests.
- 2026-07-06: `python -m reviewflow.cli run --event-path examples/github_pull_request_event.json --diff-path examples/sample_pr_diff.patch --config reviewflow.config.example.yml --output-dir .reviewflow --dry-run` passed and generated `.reviewflow/review-context.json`, `.reviewflow/review-report.json`, and `.reviewflow/review-summary.md`.
- 2026-07-07: On `main`, `python -m pytest` passed with 7 tests.
- 2026-07-07: On `main`, `python -m reviewflow.cli run --event-path examples/github_pull_request_event.json --diff-path examples/sample_pr_diff.patch --config reviewflow.config.example.yml --output-dir .reviewflow --dry-run` passed.
- 2026-07-07: On `main`, `python -m compileall reviewflow tests` passed when run separately after pytest to avoid concurrent `__pycache__` writes on Windows.
- 2026-07-11: `python -m pytest` passed with 8 tests after adding Delivery Audit.
- 2026-07-11: `python -m compileall reviewflow tests` and `python -m ruff check reviewflow tests` passed.
- 2026-07-11: The Delivery Audit self-check generated all four artifacts with a 90% evidence score and correctly reported missing deployment evidence.
- 2026-07-11: Desktop and 375px mobile HTML report checks passed; the mobile document had no horizontal overflow.
- 2026-07-11: The fusion build passed 8 tests, Ruff, and compileall; a real audit generated seven artifacts, and two CLI sync runs produced one append followed by one deduplicated skip.
- 2026-07-11: Security Scan added 14 Python AST checks, four GitHub Actions checks, one tracked-sensitive-filename check, safe SARIF import/export, CI thresholds, and three report artifacts. Nine tests, Ruff, and compileall passed; self-scan fell from three unpinned-action findings to zero after pinning official actions and removing unused write permissions.
