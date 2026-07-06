# ReviewFlow AI Project Instructions

## Project
- Name: ReviewFlow AI Starter
- Date: 2026-07-06
- Goal: Build an MVP GitHub PR AI pre-review pipeline with dry-run defaults.

## Stack
- Language: Python
- Runtime: Python 3.10+
- Package manager: standard Python tooling
- Test runner: pytest

## Main Directories
- `reviewflow/`: application package and CLI modules
- `prompts/`: prompt templates
- `schemas/`: JSON schemas
- `docs/`: technical and interview documentation
- `examples/`: local demo inputs
- `.github/workflows/`: GitHub Actions workflow files
- `tests/`: automated tests

## Common Commands
- Run tests: `python -m pytest`
- Run CLI demo: `python -m reviewflow.cli run --event-path examples/github_pull_request_event.json --diff-path examples/sample_pr_diff.patch --config reviewflow.config.example.yml --output-dir .reviewflow --dry-run`
- Static syntax check: `python -m compileall reviewflow tests`

## Architecture Rules
- Keep the MVP isolated in the allowed directories.
- Keep GitHub side effects disabled by default.
- Use deterministic offline mode when `REVIEWFLOW_CODEX_COMMAND` is not set.
- Treat Codex invocation as a replaceable adapter boundary.
- Build compact review context instead of loading the whole repository.

## Coding Standards
- Use explicit types at module boundaries where practical.
- Prefer small functions and simple data structures.
- Avoid unnecessary dependencies and framework code.
- Keep comments focused on constraints and non-obvious decisions.
- Keep all code, comments, filenames, README, and technical docs in English.

## Testing
- Add focused tests for parsers, context construction, report generation, and CLI smoke behavior.
- Run the available tests before final delivery.
- If a command is unavailable, document the reason and use the strongest local substitute.

## Deployment And CI
- GitHub Action must use `pull_request`, not `pull_request_target`.
- Default permissions should be minimal.
- Artifacts can be uploaded by CI.
- PR comments and review requests require explicit configuration and must stay safe for forks.

## Security
- Do not read, print, store, or commit secrets.
- Do not commit `.env`.
- Do not write tokens to logs or generated reports.
- Do not auto-merge, auto-push patches, or perform real GitHub API calls by default.
