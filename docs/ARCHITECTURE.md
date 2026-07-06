# Architecture

```text
GitHub Pull Request Event
        |
        v
GitHub Action
        |
        v
ReviewFlow CLI
        |
        +--> Diff Collector
        +--> CODEOWNERS Parser
        +--> SonarQube Adapter
        +--> Dependency Adapter
        |
        v
Context Builder
        |
        v
Codex Adapter
        |
        v
Report Generator
        |
        +--> JSON Report
        +--> Markdown Summary
        +--> Optional Patch Diff
        |
        v
GitHub Client
        +--> Optional PR Comment
        +--> Optional Reviewer Request
```

## Design Principles

### 1. Diff-first Context

The system should not send the whole repository to the model by default. It should prioritize:

1. PR diff.
2. Changed files.
3. Related tests.
4. Dependency manifests.
5. CODEOWNERS.
6. SonarQube and dependency risk summaries.
7. README and AGENTS.md.

### 2. Deterministic Signals Before AI

SonarQube and dependency scanners provide deterministic signals. Codex should explain, connect, and supplement these signals instead of replacing them.

### 3. Human Review Boundary

ReviewFlow AI is not an approver. It produces a pre-review report and routes reviewers. Code Owners still make the final merge decision.

### 4. Safe Defaults

All write operations are dry-run by default. API writes must be explicitly enabled by configuration and environment variables.

## Main Components

### Diff Collector
Parses unified diff and changed file metadata.

### CODEOWNERS Parser
Maps changed files to owners using a minimal pattern-matching implementation.

### SonarQube Adapter
Normalizes quality gate, vulnerabilities, bugs, code smells, and coverage on new code.

### Dependency Adapter
Detects dependency file changes and normalizes dependency alert input.

### Context Builder
Builds a compact JSON context for Codex review under a configurable character/token budget.

### Codex Adapter
Uses an external command if configured, otherwise returns deterministic offline stub output.

### Report Generator
Normalizes findings, validates the report shape against `schemas/review_report.schema.json` when `jsonschema` is available, and generates machine-readable JSON plus human-readable Markdown.

### GitHub Client
Posts comments and requests reviewers only when write mode is explicitly enabled.

## Current MVP Implementation Notes

- The CLI writes `review-context.json`, `review-report.json`, and `review-summary.md`.
- The offline Codex adapter detects the bundled demo authorization bypass and dependency-manifest change deterministically.
- GitHub write operations are represented by a dry-run client boundary; real API calls are intentionally deferred.
- The example config exits `0` for the bundled demo report unless P0 or explicitly enabled blocking conditions are present.
