# Implementation Checklist

## Phase 0: Checkpoint

- [x] Run `git status`.
- [x] Commit current state before changes.
- [x] Confirm no secrets are staged.

## Phase 1: Project Skeleton

- [x] Create `reviewflow/` package.
- [x] Create `prompts/`, `schemas/`, `examples/`, `docs/`.
- [x] Add `pyproject.toml`.
- [x] Add `.gitignore`.

## Phase 2: Core Parsers

- [x] Implement diff parser.
- [x] Implement CODEOWNERS parser.
- [x] Add parser tests.

## Phase 3: Adapters

- [x] Implement SonarQube JSON adapter.
- [x] Implement dependency adapter.
- [x] Add sample JSON inputs.

## Phase 4: Context Builder

- [x] Build compact context.
- [x] Add max context budget.
- [x] Include repository guidance from `AGENTS.md` if available.

## Phase 5: Codex Adapter

- [x] Implement external command mode.
- [x] Implement offline stub mode.
- [x] Add timeout and error handling.

## Phase 6: Reports

- [x] Generate JSON report.
- [x] Generate Markdown report.
- [x] Validate report against schema.

## Phase 7: CLI

- [x] Add `python -m reviewflow.cli run`.
- [x] Add dry-run behavior.
- [x] Add clear output paths.

## Phase 8: GitHub Action

- [x] Add PR workflow.
- [x] Install dependencies.
- [x] Run tests.
- [x] Run CLI.
- [x] Upload artifacts.
- [x] Optional PR comment.

## Phase 9: Documentation

- [x] Update README.
- [x] Update architecture doc.
- [x] Add interview script.

## Phase 10: Acceptance

- [x] `python -m pytest` passes.
- [x] Smoke command generates `.reviewflow/review-report.json`.
- [x] Smoke command generates `.reviewflow/review-summary.md`.
- [x] GitHub workflow file is valid YAML.
