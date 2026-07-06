# ReviewFlow AI Memory

## Architecture Decisions
- 2026-07-06: The MVP will be implemented as a Python package with a `python -m reviewflow.cli run` entry point.
- 2026-07-06: The first implementation will default to dry-run behavior and deterministic offline review output.
- 2026-07-06: The first implementation will avoid mandatory third-party runtime dependencies; tests may use `pytest`.

## Design Tradeoffs
- YAML support may be implemented as a small MVP parser if no YAML dependency is available.
- Real SonarQube, Dependabot, Codex, and GitHub API integrations are adapter boundaries, with local sample/offline behavior for the MVP.

## Known Issues
- No existing application code was present at project start.

## External Resources
- Source objective file: `C:\Users\DW\.codex\attachments\9e177ca9-5eec-41ac-a1a5-db71f65ac97c\goal-objective.md`
- Starter archive: `C:\Users\DW\Downloads\reviewflow_ai_starter.zip`

## Validation Record
- Pending initial implementation and test run.
