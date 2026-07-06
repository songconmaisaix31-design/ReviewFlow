# ReviewFlow AI

ReviewFlow AI is a GitHub pull-request pre-review pipeline. It combines PR diff context, CODEOWNERS routing, SonarQube quality signals, dependency risk signals, and Codex semantic review into a structured report before human Code Owner review.

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
