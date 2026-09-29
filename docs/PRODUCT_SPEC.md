# Product Spec: ReviewFlow AI

## One-line Description

ReviewFlow AI is a pull-request pre-review pipeline that combines deterministic CI signals and AI semantic review to produce structured risk reports before human Code Owner approval.

ReviewFlow Delivery Audit is a local-first acceptance assistant for non-technical buyers who need evidence before paying for or launching an AI application.

## Problem

Manual PR review is expensive and inconsistent. Static analysis catches style and quality issues, but it usually misses business logic regressions, missing tests, and cross-file reasoning. LLM review can help, but raw LLM comments are noisy unless grounded by diff, ownership, dependency, and CI signals.

## Goals

### Repository Security Scan MVP
- Scan Python source with deterministic AST rules for common security and correctness defects.
- Check repository and GitHub Actions security boundaries without opening secret files.
- Import and deduplicate SARIF from CodeQL, Semgrep, Trivy, and other compatible tools.
- Generate JSON, Markdown, and SARIF artifacts with CI-friendly severity thresholds.
- Never claim that a clean report proves the repository is vulnerability-free.

### Delivery Audit MVP
- Inspect a repository without reading secret files or calling external services.
- Separate repository-observed evidence from customer-supplied acceptance evidence.
- Check implementation, tests, delivery automation, documentation, and acceptance claims.
- Generate JSON, Chinese Markdown, and Chinese HTML client reports.
- Export a source-free content brief for the Cheat on Content experiment loop.
- Finish a useful local audit in one command.

### Delivery Audit Acceptance Criteria
- `python -m reviewflow.cli audit --repo-path . --output-dir .reviewflow-audit` exits successfully.
- Seven artifacts are generated: JSON, Markdown, HTML, a content brief, Cheat-compatible candidate JSON/Markdown, and a Wiki knowledge capsule.
- The report never claims production usage, customer acceptance, or security assurance without supplied evidence.
- Secret files and ignored runtime directories are not opened or included in report artifacts.
- `sync-content` appends one candidate only to an initialized Cheat on Content project and is idempotent by candidate ID.
- ReviewFlow never writes directly into the Personal Wiki; the capsule remains evidence input for the Wiki's own approval workflow.

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
- Security certification or penetration testing.
- Proving production traffic from source code alone.
- Guaranteeing content performance or follower growth.
- Reimplementing full cross-file taint analysis, dependency databases, or git-history secret scanning.

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
