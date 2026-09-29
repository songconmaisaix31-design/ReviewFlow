# ReviewFlow AI

ReviewFlow AI is a GitHub pull-request pre-review pipeline. It combines PR diff context, CODEOWNERS routing, SonarQube quality signals, dependency risk signals, and Codex semantic review into a structured report before human Code Owner review.

It also includes a local-first Delivery Audit mode for buyers who need evidence before paying for or launching an AI application.

The Repository Security Scan adds a safe built-in Python AST baseline and aggregates SARIF from specialist scanners without copying external source snippets or possible secret values into ReviewFlow artifacts.

## MVP Scope

Included:
- GitHub PR event workflow.
- Changed-file and diff collection.
- CODEOWNERS parsing.
- SonarQube result normalization from JSON input.
- Dependency risk normalization from manifest changes and sample alerts.
- Compact review context generation.
- Codex adapter with external command mode and offline stub mode.
- JSON and Markdown report generation.
- Dry-run GitHub comment and reviewer routing.

Not included in v0.1:
- GitLab support.
- Dashboard.
- Auto-merge.
- Auto-push patch commits.
- Full-repository RAG.

## Local Smoke Run

```bash
python -m pytest
python -m reviewflow.cli run \
  --event-path examples/github_pull_request_event.json \
  --diff-path examples/sample_pr_diff.patch \
  --config reviewflow.config.example.yml \
  --output-dir .reviewflow \
  --dry-run
```

Expected outputs:

```text
.reviewflow/review-context.json
.reviewflow/review-report.json
.reviewflow/review-summary.md
```

The bundled sample intentionally produces a `HIGH` / `WARNING` report because it contains an authorization bypass signal and a high-severity dependency alert. The command still exits `0` with the example config because `fail_on_p1` is disabled for local demo runs.

## Delivery Audit

Run a deterministic repository evidence audit without external credentials:

```bash
python -m reviewflow.cli audit \
  --repo-path . \
  --evidence-path examples/delivery_evidence.json \
  --output-dir .reviewflow-audit
```

Expected outputs:

```text
.reviewflow-audit/delivery-audit.json
.reviewflow-audit/delivery-audit.md
.reviewflow-audit/delivery-audit.html
.reviewflow-audit/content-brief.md
.reviewflow-audit/content-candidates.json
.reviewflow-audit/content-candidates.md
.reviewflow-audit/wiki-capsule.json
```

The content brief contains no source code or client paths and can enter the Cheat on Content blind-prediction and T+3 retrospective loop. The audit does not certify security or infer production acceptance from repository structure.

To append the generated candidate to an initialized local Cheat on Content project:

```bash
python -m reviewflow.cli sync-content \
  --audit-path .reviewflow-audit/delivery-audit.json \
  --content-project ../my-content-project
```

The target must contain `.cheat-state.json`. Repeating the command with the same audit is safe: an existing candidate ID is skipped. `wiki-capsule.json` is review input only; ReviewFlow never writes directly into the Personal Wiki.

## Repository Security Scan

Run the offline built-in scan:

```bash
python -m reviewflow.cli scan \
  --repo-path . \
  --output-dir .reviewflow-scan \
  --fail-on P1
```

Import SARIF from specialist scanners when available:

```bash
python -m reviewflow.cli scan \
  --repo-path . \
  --output-dir .reviewflow-scan \
  --sarif codeql.sarif \
  --sarif semgrep.sarif \
  --sarif trivy.sarif \
  --fail-on P1
```

Expected outputs:

```text
.reviewflow-scan/security-scan.json
.reviewflow-scan/security-scan.md
.reviewflow-scan/security-scan.sarif
```

Built-in checks cover common Python execution, injection, TLS, deserialization, temporary-file, weak-hash, timeout, exception, and mutable-default defects plus GitHub Actions and tracked sensitive-filename boundaries. A clean result is not proof of security; use CodeQL/Semgrep for deeper source analysis, OSV-Scanner/Trivy for dependencies and deployment artifacts, and Gitleaks for dedicated secret-history scanning.

## Codex Integration

Set `REVIEWFLOW_CODEX_COMMAND` to an executable command that accepts the generated review context and returns report JSON on stdout.

Example:

```bash
export REVIEWFLOW_CODEX_COMMAND="python scripts/mock_codex_review.py"
```

If `REVIEWFLOW_CODEX_COMMAND` is not set, ReviewFlow AI uses offline stub mode so demos and tests can run without external credentials.

## GitHub Action

The workflow lives at:

```text
.github/workflows/ai-review.yml
```

It runs on pull request updates, builds review context, generates reports, uploads artifacts, and can optionally post a PR comment.

## Configuration

Copy the example config:

```bash
cp reviewflow.config.example.yml reviewflow.config.yml
```

Then adjust:
- token budget
- blocking thresholds
- SonarQube input path
- dependency alert input path
- GitHub write behavior
- Codex command

### SonarQube and Dependabot Inputs

For local demos, `sonarqube.input_path` can point to a JSON file shaped like `examples/sample_sonar_result.json`, and `dependency.alert_input_path` can point to a JSON file shaped like `examples/sample_dependabot_alerts.json`.

In CI, generate or download those JSON artifacts before the ReviewFlow step, then pass their paths through `reviewflow.config.yml` or the `REVIEWFLOW_SONAR_INPUT` environment variable for SonarQube.

### Blocking Behavior

The CLI exits non-zero when configured blocking rules match:
- `fail_on_p0`
- `fail_on_p1`
- `fail_on_quality_gate_failed`
- `fail_on_critical_dependency`

The example config keeps `fail_on_p1` and `fail_on_quality_gate_failed` disabled so the demo can show risk findings without failing the local smoke command.

## Safety

ReviewFlow AI is safe-by-default:
- dry-run enabled by default
- no auto-merge
- no auto-push patch
- no secret logging
- optional external service calls
