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
from reviewflow.diff_collector import collect_diff
from reviewflow.report_generator import build_report, should_fail, write_report_artifacts
from reviewflow.sonar_adapter import load_sonar_summary, sonar_findings


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return _run(args)
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
    return parser


if __name__ == "__main__":
    sys.exit(main())
