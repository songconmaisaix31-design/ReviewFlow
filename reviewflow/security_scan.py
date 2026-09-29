"""Local repository security scanning and SARIF aggregation."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlparse


SEVERITY_ORDER = {"P0": 4, "P1": 3, "P2": 2, "P3": 1}
SKIP_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".reviewflow",
    ".reviewflow-audit",
    ".reviewflow-scan",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
    "node_modules",
    "vendor",
    "venv",
}
MAX_SARIF_RESULTS = 5000
MAX_SARIF_BYTES = 20_000_000
TOOL_NAMES = ("codeql", "semgrep", "bandit", "osv-scanner", "trivy", "gitleaks")


def scan_repository(
    repo_path: str | Path,
    *,
    sarif_paths: list[str | Path] | None = None,
    max_files: int = 2000,
    max_file_bytes: int = 1_000_000,
) -> dict[str, Any]:
    root = Path(repo_path).resolve()
    if not root.is_dir():
        raise ValueError(f"Repository path is not a directory: {root}")
    if max_files < 1 or max_file_bytes < 1:
        raise ValueError("Scan limits must be positive integers.")

    findings: list[dict[str, Any]] = []
    scanned_files = 0
    skipped_files = 0
    for path in _safe_source_files(root):
        if scanned_files >= max_files:
            skipped_files += 1
            continue
        if path.stat().st_size > max_file_bytes:
            skipped_files += 1
            continue
        relative_path = path.relative_to(root).as_posix()
        if path.suffix.lower() == ".py":
            findings.extend(_scan_python(path, relative_path))
            scanned_files += 1
        elif _is_workflow(path, root):
            findings.extend(_scan_workflow(path, relative_path))
            scanned_files += 1

    findings.extend(_tracked_sensitive_file_findings(root))
    imported_sarif = []
    for sarif_path in sarif_paths or []:
        path = Path(sarif_path)
        findings.extend(import_sarif(path))
        imported_sarif.append(path.name)

    findings = _deduplicate_and_sort(findings)
    risk_level = _risk_level(findings)
    status = "FAILED" if any(item["severity"] in {"P0", "P1"} for item in findings) else "WARNING" if findings else "PASSED"
    return {
        "schema_version": "1.0",
        "scan_type": "repository_security",
        "status": status,
        "risk_level": risk_level,
        "summary": {
            "files_scanned": scanned_files,
            "files_skipped": skipped_files,
            "findings": len(findings),
            "severity_counts": {
                severity: sum(item["severity"] == severity for item in findings)
                for severity in SEVERITY_ORDER
            },
            "imported_sarif": imported_sarif,
            "tool_readiness": {name: shutil.which(name) is not None for name in TOOL_NAMES},
        },
        "findings": findings,
        "limitations": [
            "A clean report does not prove that the repository is vulnerability-free.",
            "Built-in analysis is Python-focused and mostly intrafile.",
            "Dependency reachability, git-history secrets, containers, IaC, and cross-file taint require specialist scanners.",
            "External SARIF messages and source snippets are intentionally discarded to avoid secret leakage.",
        ],
    }


def import_sarif(path: str | Path) -> list[dict[str, Any]]:
    sarif_path = Path(path)
    if sarif_path.stat().st_size > MAX_SARIF_BYTES:
        raise ValueError(f"SARIF file exceeds {MAX_SARIF_BYTES} bytes: {sarif_path.name}")
    payload = json.loads(sarif_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("runs", []), list):
        raise ValueError(f"Invalid SARIF structure: {sarif_path.name}")
    findings: list[dict[str, Any]] = []
    for run in payload.get("runs", []):
        if not isinstance(run, dict):
            continue
        tool = run.get("tool", {})
        driver = tool.get("driver", {}) if isinstance(tool, dict) else {}
        tool_name = _safe_identifier(driver.get("name") if isinstance(driver, dict) else None, "external-sarif")
        results = run.get("results", [])
        if not isinstance(results, list):
            continue
        for result in results[:MAX_SARIF_RESULTS]:
            if not isinstance(result, dict):
                continue
            rule_id = _safe_identifier(result.get("ruleId"), "external-rule")
            location = _sarif_location(result)
            severity = _sarif_severity(result)
            findings.append(
                _finding(
                    rule_id=rule_id,
                    severity=severity,
                    category="security",
                    file=location[0],
                    line=location[1],
                    title=f"External scanner finding: {rule_id}",
                    evidence=f"{tool_name} reported rule {rule_id}; external message and source snippet were redacted.",
                    recommendation=f"Open the original {tool_name} report and review rule {rule_id} at the reported location.",
                    confidence="high" if severity in {"P0", "P1"} else "medium",
                    source=f"sarif:{tool_name}",
                )
            )
    return _deduplicate_and_sort(findings)


def write_security_scan_artifacts(report: dict[str, Any], output_dir: str | Path) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output / "security-scan.json",
        "markdown": output / "security-scan.md",
        "sarif": output / "security-scan.sarif",
    }
    paths["json"].write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths["markdown"].write_text(render_security_markdown(report), encoding="utf-8")
    paths["sarif"].write_text(json.dumps(render_sarif(report), indent=2) + "\n", encoding="utf-8")
    return paths


def render_security_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# ReviewFlow Repository Security Scan",
        "",
        f"- Status: {report['status']}",
        f"- Risk level: {report['risk_level']}",
        f"- Files scanned: {summary['files_scanned']}",
        f"- Findings: {summary['findings']}",
        "",
        "## Findings",
        "",
    ]
    if not report["findings"]:
        lines.append("- No findings. This does not prove the repository is vulnerability-free.")
    for finding in report["findings"]:
        location = finding["file"]
        if finding.get("line"):
            location = f"{location}:{finding['line']}"
        lines.extend(
            [
                f"### {finding['severity']} {finding['rule_id']} - {finding['title']}",
                f"- Location: `{location}`",
                f"- Category: {finding['category']}",
                f"- Source: {finding['source']}",
                f"- Confidence: {finding['confidence']}",
                f"- Evidence: {finding['evidence']}",
                f"- Recommendation: {finding['recommendation']}",
                "",
            ]
        )
    lines.extend(["## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    return "\n".join(lines).rstrip() + "\n"


def render_sarif(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {"driver": {"name": "ReviewFlow", "informationUri": "https://github.com/"}},
                "results": [
                    {
                        "ruleId": finding["rule_id"],
                        "level": _sarif_level(finding["severity"]),
                        "message": {"text": finding["evidence"]},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": finding["file"]},
                                    "region": {"startLine": finding["line"] or 1},
                                }
                            }
                        ],
                    }
                    for finding in report["findings"]
                ],
            }
        ],
    }


def scan_should_fail(report: dict[str, Any], fail_on: str) -> bool:
    if fail_on.lower() == "none":
        return False
    threshold = SEVERITY_ORDER[fail_on.upper()]
    return any(SEVERITY_ORDER.get(item["severity"], 0) >= threshold for item in report["findings"])


class _PythonVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.findings: list[dict[str, Any]] = []
        self.aliases: dict[str, str] = {}

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        for alias in node.names:
            local_name = alias.asname or alias.name.split(".")[0]
            self.aliases[local_name] = alias.name

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        if node.module:
            for alias in node.names:
                self.aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        name = self.resolve_call_name(node.func)
        if name in {"eval", "exec"}:
            self.add("RF-PY001", "P1", "security", node, "Dynamic code execution", f"Call to {name} detected.", "Remove dynamic execution or use a constrained parser.", "CWE-95")
        if name == "os.system":
            self.add("RF-PY002", "P1", "security", node, "Shell command execution", "Call to os.system detected.", "Use subprocess with an argument list and shell disabled.", "CWE-78")
        if name.startswith("subprocess.") and _keyword_bool(node, "shell", True):
            self.add("RF-PY003", "P1", "security", node, "Subprocess shell enabled", "A subprocess call enables shell=True.", "Pass an argument list with shell=False and validate untrusted input.", "CWE-78")
        if name.startswith("requests.") and _keyword_bool(node, "verify", False):
            self.add("RF-PY004", "P1", "security", node, "TLS verification disabled", "A requests call sets verify=False.", "Enable certificate verification and configure a trusted CA bundle when required.", "CWE-295")
        if name == "ssl._create_unverified_context":
            self.add("RF-PY005", "P1", "security", node, "Unverified SSL context", "An unverified SSL context is created.", "Use ssl.create_default_context and verify peer certificates.", "CWE-295")
        if name == "yaml.load" and not _uses_safe_yaml_loader(node):
            self.add("RF-PY006", "P1", "security", node, "Unsafe YAML loading", "yaml.load is used without a safe loader.", "Use yaml.safe_load for untrusted YAML.", "CWE-502")
        if name == "tempfile.mktemp":
            self.add("RF-PY007", "P1", "security", node, "Insecure temporary file", "tempfile.mktemp is vulnerable to race conditions.", "Use NamedTemporaryFile or mkstemp.", "CWE-377")
        if name in {"pickle.load", "pickle.loads"}:
            self.add("RF-PY008", "P2", "security", node, "Unsafe deserialization boundary", f"Call to {name} can execute code for untrusted input.", "Use a data-only format or prove that the input is trusted.", "CWE-502", "medium")
        if name in {"hashlib.md5", "hashlib.sha1"}:
            self.add("RF-PY009", "P2", "security", node, "Weak cryptographic hash", f"Call to {name} detected.", "Use SHA-256 or stronger for security-sensitive hashing.", "CWE-327", "medium")
        if name.endswith(".execute") or name.endswith(".executemany"):
            if node.args and _is_dynamic_string(node.args[0]):
                self.add("RF-PY010", "P1", "security", node, "Dynamically constructed SQL", "A dynamic string is passed directly to a database execute call.", "Use parameterized SQL and bind values separately.", "CWE-89")
        if name.startswith("requests.") and _is_http_method(name) and not _has_keyword(node, "timeout"):
            self.add("RF-PY011", "P2", "reliability", node, "HTTP request without timeout", "A requests call has no explicit timeout.", "Set a finite connect/read timeout and handle timeout failures.", "CWE-400", "medium")
        if name == "urllib.request.urlopen" and not _has_keyword(node, "timeout"):
            self.add("RF-PY011", "P2", "reliability", node, "HTTP request without timeout", "urlopen has no explicit timeout.", "Set a finite timeout and handle timeout failures.", "CWE-400", "medium")
        if name.endswith("jwt.decode") and _jwt_verification_disabled(node):
            self.add("RF-PY012", "P1", "security", node, "JWT signature verification disabled", "JWT decode options disable signature verification.", "Verify signatures and restrict accepted algorithms.", "CWE-347")
        self.generic_visit(node)

    def resolve_call_name(self, node: ast.AST) -> str:
        name = _call_name(node)
        root, separator, remainder = name.partition(".")
        resolved_root = self.aliases.get(root, root)
        return f"{resolved_root}.{remainder}" if separator else resolved_root

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:  # noqa: N802
        if node.type is None:
            self.add("RF-PY013", "P2", "correctness", node, "Bare exception handler", "A bare except catches system-exiting exceptions and hides failure types.", "Catch the narrowest expected exception and preserve failure context.", "CWE-396", "medium")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        if any(_is_mutable_default(default) for default in (*node.args.defaults, *node.args.kw_defaults) if default):
            self.add("RF-PY014", "P2", "correctness", node, "Mutable default argument", "A function uses a mutable default value shared across calls.", "Use None and create the mutable value inside the function.", "CWE-665", "high")
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def add(
        self,
        rule_id: str,
        severity: str,
        category: str,
        node: ast.AST,
        title: str,
        evidence: str,
        recommendation: str,
        cwe: str,
        confidence: str = "high",
    ) -> None:
        self.findings.append(
            _finding(
                rule_id=rule_id,
                severity=severity,
                category=category,
                file=self.file_path,
                line=getattr(node, "lineno", None),
                title=title,
                evidence=evidence,
                recommendation=recommendation,
                confidence=confidence,
                source="reviewflow-python-ast",
                cwe=cwe,
            )
        )


def _scan_python(path: Path, relative_path: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=relative_path)
    except SyntaxError as exc:
        return [
            _finding(
                rule_id="RF-PY000",
                severity="P2",
                category="correctness",
                file=relative_path,
                line=exc.lineno,
                title="Python syntax error",
                evidence="The file could not be parsed as Python source.",
                recommendation="Fix the syntax error before relying on deeper static analysis.",
                confidence="high",
                source="reviewflow-python-ast",
            )
        ]
    visitor = _PythonVisitor(relative_path)
    visitor.visit(tree)
    return visitor.findings


def _scan_workflow(path: Path, relative_path: str) -> list[dict[str, Any]]:
    findings = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for line_number, line in enumerate(text.splitlines(), start=1):
        if re.match(r"^\s*pull_request_target\s*:", line):
            findings.append(_finding("RF-GH001", "P1", "security", relative_path, line_number, "Privileged pull request trigger", "The workflow uses pull_request_target.", "Use pull_request for untrusted fork code, or isolate the privileged workflow from checkout and execution.", "high", "reviewflow-workflow", "CWE-829"))
        if re.match(r"^\s*permissions\s*:\s*write-all\s*$", line):
            findings.append(_finding("RF-GH002", "P1", "security", relative_path, line_number, "Broad workflow permissions", "The workflow grants write-all permissions.", "Declare the minimum required permissions explicitly.", "high", "reviewflow-workflow", "CWE-250"))
        if re.match(r"^\s+[a-z-]+\s*:\s*write\s*$", line):
            findings.append(_finding("RF-GH004", "P2", "security", relative_path, line_number, "Workflow has write permission", "A workflow permission grants write access.", "Confirm the write scope is required and reduce it to read or none when possible.", "medium", "reviewflow-workflow", "CWE-250"))
        uses_match = re.search(r"\buses\s*:\s*([^\s#]+)", line)
        if uses_match and _is_unpinned_action(uses_match.group(1)):
            findings.append(_finding("RF-GH003", "P2", "supply-chain", relative_path, line_number, "Action is not commit-pinned", "A third-party action is referenced by a mutable tag or branch.", "Pin the action to a reviewed 40-character commit SHA and document the release tag.", "high", "reviewflow-workflow", "CWE-829"))
    return findings


def _tracked_sensitive_file_findings(root: Path) -> list[dict[str, Any]]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    findings = []
    for raw_path in result.stdout.decode("utf-8", errors="replace").split("\0"):
        if raw_path and _is_sensitive_path(raw_path):
            safe_path = _safe_repo_path(raw_path)
            findings.append(
                _finding(
                    "RF-REPO001",
                    "P1",
                    "security",
                    safe_path,
                    None,
                    "Sensitive filename is tracked by Git",
                    "Git tracks a file whose name commonly contains credentials; file contents were not opened.",
                    "Remove the file from version control, rotate any exposed credential, and add a safe ignore rule.",
                    "high",
                    "reviewflow-repository",
                    "CWE-798",
                )
            )
    return findings


def _safe_source_files(root: Path) -> list[Path]:
    paths = []
    for current, directories, files in os.walk(root):
        directories[:] = sorted(name for name in directories if name not in SKIP_DIRECTORIES)
        current_path = Path(current)
        for filename in sorted(files):
            path = current_path / filename
            if path.is_symlink():
                continue
            try:
                path.resolve().relative_to(root)
            except ValueError:
                continue
            relative = path.relative_to(root).as_posix()
            if _is_sensitive_path(relative):
                continue
            if path.suffix.lower() == ".py" or _is_workflow(path, root):
                paths.append(path)
    return paths


def _is_workflow(path: Path, root: Path) -> bool:
    relative = path.relative_to(root).as_posix()
    return relative.startswith(".github/workflows/") and path.suffix.lower() in {".yml", ".yaml"}


def _is_sensitive_path(path: str) -> bool:
    name = PurePosixPath(path.replace("\\", "/")).name.lower()
    if name in {".env.example", ".env.sample", "id_rsa.pub", "id_dsa.pub"}:
        return False
    return (
        name == ".env"
        or name.startswith(".env.")
        or name in {"credentials.json", "service-account.json", "id_rsa", "id_dsa"}
        or Path(name).suffix in {".key", ".pem", ".p12", ".pfx"}
    )


def _safe_repo_path(path: str) -> str:
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "-", path.replace("\\", "/"))
    candidate = PurePosixPath(cleaned)
    if candidate.is_absolute() or ".." in candidate.parts or re.match(r"^[A-Za-z]:", cleaned):
        return "<unsafe-path>"
    return candidate.as_posix()


def _finding(
    rule_id: str,
    severity: str,
    category: str,
    file: str,
    line: int | None,
    title: str,
    evidence: str,
    recommendation: str,
    confidence: str,
    source: str,
    cwe: str | None = None,
) -> dict[str, Any]:
    key = f"{rule_id}|{file}|{line or 0}"
    return {
        "id": f"{rule_id}-{hashlib.sha256(key.encode('utf-8')).hexdigest()[:8]}",
        "rule_id": rule_id,
        "severity": severity if severity in SEVERITY_ORDER else "P3",
        "category": category,
        "file": file,
        "line": line,
        "title": title,
        "evidence": evidence,
        "recommendation": recommendation,
        "confidence": confidence,
        "source": source,
        "cwe": cwe,
    }


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _has_keyword(node: ast.Call, name: str) -> bool:
    return any(keyword.arg == name for keyword in node.keywords)


def _keyword_bool(node: ast.Call, name: str, value: bool) -> bool:
    return any(keyword.arg == name and isinstance(keyword.value, ast.Constant) and keyword.value.value is value for keyword in node.keywords)


def _uses_safe_yaml_loader(node: ast.Call) -> bool:
    for keyword in node.keywords:
        if keyword.arg == "Loader" and _call_name(keyword.value).split(".")[-1] in {"SafeLoader", "CSafeLoader"}:
            return True
    return False


def _is_dynamic_string(node: ast.AST) -> bool:
    return isinstance(node, (ast.JoinedStr, ast.BinOp)) or (
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format"
    )


def _is_http_method(name: str) -> bool:
    return name.split(".")[-1].lower() in {"delete", "get", "head", "options", "patch", "post", "put", "request"}


def _jwt_verification_disabled(node: ast.Call) -> bool:
    for keyword in node.keywords:
        if keyword.arg != "options" or not isinstance(keyword.value, ast.Dict):
            continue
        for key, value in zip(keyword.value.keys, keyword.value.values):
            if isinstance(key, ast.Constant) and key.value == "verify_signature":
                return isinstance(value, ast.Constant) and value.value is False
    return False


def _is_mutable_default(node: ast.AST) -> bool:
    if isinstance(node, (ast.Dict, ast.List, ast.Set)):
        return True
    return isinstance(node, ast.Call) and _call_name(node.func) in {"dict", "list", "set"}


def _is_unpinned_action(value: str) -> bool:
    if value.startswith(("./", "docker://")) or "@" not in value:
        return False
    reference = value.rsplit("@", 1)[1]
    return re.fullmatch(r"[0-9a-fA-F]{40}", reference) is None


def _sarif_location(result: dict[str, Any]) -> tuple[str, int | None]:
    try:
        physical = result["locations"][0]["physicalLocation"]
        uri = str(physical.get("artifactLocation", {}).get("uri", "<unknown>"))
        line = physical.get("region", {}).get("startLine")
    except (IndexError, KeyError, TypeError):
        return "<unknown>", None
    parsed = urlparse(uri)
    if parsed.scheme == "file":
        return "<external>", int(line) if isinstance(line, int) else None
    raw_path = unquote(parsed.path if parsed.scheme else uri).replace("\\", "/").lstrip("/")
    candidate = PurePosixPath(raw_path)
    if parsed.scheme not in {"", "file"} or candidate.is_absolute() or ".." in candidate.parts or re.match(r"^[A-Za-z]:", raw_path):
        return "<external>", int(line) if isinstance(line, int) else None
    return candidate.as_posix() or "<unknown>", int(line) if isinstance(line, int) else None


def _sarif_severity(result: dict[str, Any]) -> str:
    score = result.get("properties", {}).get("security-severity")
    try:
        numeric_score = float(score)
    except (TypeError, ValueError):
        numeric_score = 0.0
    if numeric_score >= 9.0:
        return "P0"
    if numeric_score >= 7.0:
        return "P1"
    if numeric_score >= 4.0:
        return "P2"
    return {"error": "P1", "warning": "P2", "note": "P3", "none": "P3"}.get(str(result.get("level", "warning")).lower(), "P2")


def _safe_identifier(value: Any, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.:/-]", "-", str(value or ""))[:80].strip("-")
    return cleaned or fallback


def _deduplicate_and_sort(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique = {}
    for finding in findings:
        key = (finding["source"], finding["rule_id"], finding["file"], finding.get("line"))
        unique.setdefault(key, finding)
    return sorted(
        unique.values(),
        key=lambda item: (-SEVERITY_ORDER[item["severity"]], item["file"], item.get("line") or 0, item["rule_id"]),
    )


def _risk_level(findings: list[dict[str, Any]]) -> str:
    highest = max((SEVERITY_ORDER[item["severity"]] for item in findings), default=0)
    return {4: "CRITICAL", 3: "HIGH", 2: "MEDIUM", 1: "LOW", 0: "LOW"}[highest]


def _sarif_level(severity: str) -> str:
    return {"P0": "error", "P1": "error", "P2": "warning", "P3": "note"}[severity]
