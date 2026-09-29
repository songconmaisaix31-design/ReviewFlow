"""Command line entry point for ReviewFlow AI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from reviewflow.codex_adapter import run_codex_review
from reviewflow.codeowners_parser import load_codeowners, owners_for_files
from reviewflow.config import load_config
from reviewflow.context_builder import build_review_context
from reviewflow.dependency_adapter import dependency_findings, load_dependency_summary
from reviewflow.delivery_audit import audit_repository, sync_content_candidate, write_delivery_audit_artifacts
from reviewflow.diff_collector import collect_diff
from reviewflow.report_generator import build_report, should_fail, write_report_artifacts
from reviewflow.security_scan import scan_repository, scan_should_fail, write_security_scan_artifacts
from reviewflow.sonar_adapter import load_sonar_summary, sonar_findings


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return _run(args)
    if args.command == "audit":
        return _audit(args)
    if args.command == "sync-content":
        return _sync_content(args)
    if args.command == "scan":
        return _scan(args)
    parser.error("Unsupported command")
    return 2


def _run(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    if args.dry_run:
        config.setdefault("review", {})["dry_run"] = True
        config.setdefault("github", {})["dry_run"] = True

    event = json.loads(Path(args.event_path).read_text(encoding="utf-8"))
    diff_data = collect_diff(args.diff_path)
    changed_paths = list(diff_data["changed_file_paths"])

    owner_rules = load_codeowners(config.get("owners", {}).get("codeowners_paths", []), ".")
    owner_mapping = owners_for_files(changed_paths, owner_rules)
    sonar_summary = load_sonar_summary(config)
    dependency_summary = load_dependency_summary(config, changed_paths)

    context = build_review_context(
        event=event,
        diff_data=diff_data,
        owner_mapping=owner_mapping,
        sonar_summary=sonar_summary,
        dependency_summary=dependency_summary,
        config=config,
        repo_root=".",
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    context_path = output_dir / config.get("report", {}).get("output_context", "review-context.json")
    context_path.write_text(json.dumps(context, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    codex_result = run_codex_review(context, config)
    report = build_report(
        context=context,
        codex_result=codex_result,
        sonar_findings=sonar_findings(sonar_summary),
        dependency_findings=dependency_findings(dependency_summary),
    )
    artifact_paths = write_report_artifacts(report, output_dir, config)

    print(f"Review context: {context_path}")
    print(f"Review report: {artifact_paths['json']}")
    print(f"Review summary: {artifact_paths['markdown']}")
    if "patch" in artifact_paths:
        print(f"Review patch: {artifact_paths['patch']}")
    return 1 if should_fail(report, config) else 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reviewflow")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="Generate a ReviewFlow AI report")
    run_parser.add_argument("--event-path", required=True)
    run_parser.add_argument("--diff-path", required=True)
    run_parser.add_argument("--config", required=True)
    run_parser.add_argument("--output-dir", required=True)
    run_parser.add_argument("--dry-run", action="store_true")
    audit_parser = subparsers.add_parser("audit", help="Audit AI application delivery evidence")
    audit_parser.add_argument("--repo-path", required=True)
    audit_parser.add_argument("--output-dir", required=True)
    audit_parser.add_argument("--evidence-path")
    sync_parser = subparsers.add_parser("sync-content", help="Append an audit candidate to a local content project")
    sync_parser.add_argument("--audit-path", required=True)
    sync_parser.add_argument("--content-project", required=True)
    scan_parser = subparsers.add_parser("scan", help="Scan a local repository for security and correctness issues")
    scan_parser.add_argument("--repo-path", required=True)
    scan_parser.add_argument("--output-dir", required=True)
    scan_parser.add_argument("--sarif", action="append", default=[])
    scan_parser.add_argument("--max-files", type=int, default=2000)
    scan_parser.add_argument("--max-file-bytes", type=int, default=1_000_000)
    scan_parser.add_argument("--fail-on", choices=["none", "P0", "P1", "P2", "P3"], default="P1")
    return parser


def _audit(args: argparse.Namespace) -> int:
    report = audit_repository(args.repo_path, args.evidence_path)
    artifact_paths = write_delivery_audit_artifacts(report, args.output_dir)
    print(f"Delivery audit JSON: {artifact_paths['json']}")
    print(f"Delivery audit Markdown: {artifact_paths['markdown']}")
    print(f"Delivery audit HTML: {artifact_paths['html']}")
    print(f"Content brief: {artifact_paths['content_brief']}")
    print(f"Content candidates JSON: {artifact_paths['content_candidates_json']}")
    print(f"Content candidates Markdown: {artifact_paths['content_candidates_markdown']}")
    print(f"Wiki capsule: {artifact_paths['wiki_capsule']}")
    return 0


def _sync_content(args: argparse.Namespace) -> int:
    report = json.loads(Path(args.audit_path).read_text(encoding="utf-8"))
    if report.get("audit_type") != "delivery_evidence":
        raise ValueError("Audit file is not a ReviewFlow delivery evidence report.")
    added = sync_content_candidate(report, args.content_project)
    print("Content candidate added." if added else "Content candidate already exists; skipped.")
    return 0


def _scan(args: argparse.Namespace) -> int:
    report = scan_repository(
        args.repo_path,
        sarif_paths=args.sarif,
        max_files=args.max_files,
        max_file_bytes=args.max_file_bytes,
    )
    artifact_paths = write_security_scan_artifacts(report, args.output_dir)
    print(f"Security scan JSON: {artifact_paths['json']}")
    print(f"Security scan Markdown: {artifact_paths['markdown']}")
    print(f"Security scan SARIF: {artifact_paths['sarif']}")
    print(f"Status: {report['status']} ({report['summary']['findings']} findings)")
    return 1 if scan_should_fail(report, args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(main())
