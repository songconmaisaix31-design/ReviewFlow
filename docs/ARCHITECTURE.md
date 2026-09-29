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

## Delivery Audit Flow

```text
Local Repository + Optional Evidence Manifest
        |
        v
Safe Path Inventory
        |
        +--> Implementation Evidence
        +--> Test Evidence
        +--> Delivery Evidence
        +--> Documentation Evidence
        +--> Acceptance Claims
        |
        v
Deterministic Audit Rules
        |
        +--> JSON Evidence Record
        +--> Chinese Markdown Report
        +--> Chinese HTML Client Report
        +--> Cheat-compatible Candidate
        +--> Wiki Knowledge Capsule
```

The audit inspects file paths, not source contents. Optional claims are supplied through a JSON manifest and are supported only when every referenced relative path exists inside the audited repository. This deliberately avoids inferring real-world acceptance from code structure.

## Repository Security Scan

```text
Repository
   |
   +--> Safe file inventory
   +--> Python AST rules
   +--> Git / GitHub Actions checks
   +--> Optional SARIF files
              |
              v
      Finding normalization
              |
              +--> JSON
              +--> Markdown
              +--> SARIF 2.1.0
              +--> CI exit threshold
```

The built-in analyzer provides an offline baseline. Specialist scanners remain independent producers because each owns a different analysis domain. ReviewFlow strips external messages and snippets during SARIF import so a scanner result cannot leak a detected credential through the aggregate report.

## Local Compounding Loop

```text
Repository Evidence
        |
        v
ReviewFlow Delivery Audit
        |
        +--> Client acceptance report
        +--> Redacted candidate --> Cheat on Content --> Publish --> T+3 retrospective
        +--> Knowledge capsule -------------------------------> Personal Wiki review
                                                                    |
                                                                    v
                                                         Current truth / reusable rule
```

`sync-content` is the only write bridge. It validates that the target contains `.cheat-state.json`, appends a candidate to `candidates.md`, and skips an existing ID. There is deliberately no automatic Wiki writer: content performance and repository evidence are different evidence classes and must be reconciled by the Wiki's own growth workflow.
