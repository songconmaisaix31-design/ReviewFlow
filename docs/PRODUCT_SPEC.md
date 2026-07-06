# Product Spec: ReviewFlow AI

## One-line Description

ReviewFlow AI is a pull-request pre-review pipeline that combines deterministic CI signals and AI semantic review to produce structured risk reports before human Code Owner approval.

## Problem

Manual PR review is expensive and inconsistent. Static analysis catches style and quality issues, but it usually misses business logic regressions, missing tests, and cross-file reasoning. LLM review can help, but raw LLM comments are noisy unless grounded by diff, ownership, dependency, and CI signals.

## Goals

### P0
- Trigger on GitHub pull requests.
- Parse changed files and diff.
- Map files to CODEOWNERS.
- Normalize SonarQube and dependency risk inputs.
- Build compact review context.
- Run Codex review through an adapter.
- Generate JSON and Markdown reports.
- Upload artifacts and optionally comment on PR.

### P1
- Inline review comments.
- Better dependency advisory integration.
- Test gap detection.
- Suggested patch output.
- Quality-gate based failure policy.

### P2
- GitLab support.
- Web dashboard.
- Multi-repository governance.
- Historical review knowledge base.
- Reviewer load balancing.

## Non-goals

- Replace Code Owner review.
- Auto-merge PRs.
- Auto-push patches by default.
- Full repository indexing in v0.1.

## Users

- Backend engineers.
- Test developers.
- DevOps engineers.
- Tech leads.
- Platform teams.

## Key Workflow

1. Developer opens or updates a PR.
2. GitHub Action starts ReviewFlow AI.
3. ReviewFlow collects diff and changed files.
4. ReviewFlow parses CODEOWNERS.
5. ReviewFlow reads SonarQube and dependency risk signals.
6. ReviewFlow builds a compact context.
7. Codex performs semantic review.
8. ReviewFlow normalizes findings.
9. ReviewFlow posts a report and requests human review.

## Risk Levels

- LOW: no blocker, only P3 suggestions.
- MEDIUM: P2 issues or weak test coverage.
- HIGH: P1 issue, failed quality gate, or high dependency risk.
- CRITICAL: P0 issue or critical dependency risk.

## Success Metrics

- Local smoke command generates reports successfully.
- At least 80% of findings include file path, evidence, and recommendation.
- No secrets appear in logs or artifacts.
- PR report can be understood within 60 seconds by a human reviewer.
