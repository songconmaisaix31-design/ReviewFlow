# Repository Security Scan Specification

## Outcome

`reviewflow scan` is a local-first repository security and correctness gate. It combines high-confidence built-in checks with normalized SARIF findings from specialist scanners.

## Why This Shape

- [CodeQL](https://github.com/github/codeql) demonstrates query-based analysis and SARIF as an interchange boundary.
- [Semgrep](https://github.com/semgrep/semgrep) demonstrates multi-language rule scanning and the importance of cross-file analysis for higher recall.
- [Bandit](https://github.com/PyCQA/bandit) demonstrates focused Python AST plugins.
- [OSV-Scanner](https://github.com/google/osv-scanner) and [Trivy](https://github.com/aquasecurity/trivy) demonstrate that source analysis, dependency vulnerabilities, secrets, containers, and misconfiguration are separate scanner classes.
- [Gitleaks](https://github.com/gitleaks/gitleaks) demonstrates that secret history scanning needs a dedicated engine and redaction discipline.

ReviewFlow does not reimplement those engines. It provides a safe built-in baseline and aggregates their SARIF output without copying source snippets or possible secret values into reports.

## MVP Scope

### Built-in Python AST Rules

- dynamic execution: `eval`, `exec`
- command injection exposure: `os.system`, `subprocess` with `shell=True`
- SQL construction passed directly to `execute`
- disabled TLS verification and unverified SSL contexts
- unsafe YAML loading
- unsafe temporary-file creation
- insecure deserialization with `pickle`
- weak security hashes: MD5 and SHA-1
- network calls without an explicit timeout
- bare exception handlers
- mutable default arguments

### Repository Rules

- tracked sensitive filenames without reading their values
- GitHub Actions using `pull_request_target`
- GitHub Actions with broad write permissions
- third-party actions not pinned to a full commit SHA

### External Findings

- import one or more SARIF 2.1.0 files
- normalize rule ID, severity, path, line, source, and confidence
- discard external source snippets and scanner messages that could contain secrets
- deduplicate identical rule/path/line findings

## Non-goals

- replace CodeQL, Semgrep, Bandit, OSV-Scanner, Trivy, or Gitleaks
- claim absence of vulnerabilities
- execute untrusted project code
- install scanners automatically
- upload source code or findings
- scan `.env`, credentials, private keys, dependency trees, caches, or build outputs

## CLI

```bash
python -m reviewflow.cli scan \
  --repo-path . \
  --output-dir .reviewflow-scan \
  --sarif path/to/codeql.sarif \
  --sarif path/to/semgrep.sarif \
  --fail-on P1
```

## Outputs

- `security-scan.json`
- `security-scan.md`
- `security-scan.sarif`

## Acceptance

- vulnerable fixtures trigger the expected rule IDs and safe evidence text
- no finding contains the original source line or a secret value
- malformed Python becomes a parse finding instead of crashing the scan
- unsafe SARIF paths and messages are not copied into artifacts
- repeated SARIF findings are deduplicated
- scan limits bound file count and file size
- P0/P1 threshold returns non-zero when configured
- existing PR review and Delivery Audit tests continue to pass

## Limitations

The built-in analyzer is intentionally Python-focused and mostly intrafile. Cross-file data flow, framework-specific taint tracking, dependency reachability, git-history secret detection, containers, and IaC require specialist scanners whose SARIF can be imported.
