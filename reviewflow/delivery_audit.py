"""Deterministic, local-first delivery evidence audit."""

from __future__ import annotations

import html
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


SKIP_DIRECTORIES = {
    ".git",
    ".idea",
    ".next",
    ".pytest_cache",
    ".reviewflow",
    ".reviewflow-audit",
    ".venv",
    ".vscode",
    "build",
    "dist",
    "node_modules",
    "venv",
}
SOURCE_SUFFIXES = {".c", ".cpp", ".cs", ".go", ".java", ".js", ".jsx", ".php", ".py", ".rb", ".rs", ".ts", ".tsx"}
MANIFEST_NAMES = {"Cargo.toml", "go.mod", "package.json", "pyproject.toml", "requirements.txt"}
DEPLOYMENT_NAMES = {"Dockerfile", "compose.yml", "docker-compose.yml", "fly.toml", "netlify.toml", "vercel.json"}
SECRET_NAME_PARTS = (".env", "credential", "private_key", "secret", "token")


def audit_repository(repo_path: str | Path, evidence_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_path).resolve()
    if not root.is_dir():
        raise ValueError(f"Repository path is not a directory: {root}")

    relative_paths = _inventory_paths(root)
    path_set = set(relative_paths)
    manifests = _matching_paths(relative_paths, lambda path: Path(path).name in MANIFEST_NAMES)
    sources = _matching_paths(relative_paths, lambda path: Path(path).suffix.lower() in SOURCE_SUFFIXES)
    tests = _matching_paths(relative_paths, _is_test_path)
    ci_files = _matching_paths(relative_paths, lambda path: path.startswith(".github/workflows/"))
    deployment_files = _matching_paths(relative_paths, lambda path: Path(path).name in DEPLOYMENT_NAMES)
    documentation = _matching_paths(relative_paths, _is_documentation_path)

    claims = _load_claims(root, evidence_path, path_set)
    dimensions = [
        _dimension(
            "implementation",
            "功能实现",
            "SUPPORTED" if manifests and sources else "PARTIAL" if manifests or sources else "MISSING",
            manifests + sources[:6],
            f"发现 {len(manifests)} 个依赖清单和 {len(sources)} 个源文件。",
        ),
        _dimension(
            "tests",
            "测试证据",
            "SUPPORTED" if tests else "MISSING",
            tests[:8],
            f"发现 {len(tests)} 个测试相关文件。",
        ),
        _dimension(
            "delivery",
            "交付与部署",
            "SUPPORTED" if ci_files and deployment_files else "PARTIAL" if ci_files or deployment_files else "MISSING",
            ci_files[:4] + deployment_files[:4],
            f"发现 {len(ci_files)} 个 CI 文件和 {len(deployment_files)} 个部署文件。",
        ),
        _dimension(
            "documentation",
            "文档与接手",
            "SUPPORTED" if _has_readme(documentation) and len(documentation) > 1 else "PARTIAL" if documentation else "MISSING",
            documentation[:8],
            f"发现 {len(documentation)} 个说明文档。",
        ),
        _acceptance_dimension(claims),
    ]
    unsupported_claims = [claim for claim in claims if claim["status"] != "SUPPORTED"]
    score = round(sum(_status_score(item["status"]) for item in dimensions) / len(dimensions) * 100)
    overall_status = _overall_status(score, dimensions, unsupported_claims)
    return {
        "schema_version": "1.0",
        "audit_type": "delivery_evidence",
        "project_name": root.name,
        "evidence_snapshot_at": _evidence_snapshot_at(root, relative_paths),
        "overall_status": overall_status,
        "evidence_score": score,
        "dimensions": dimensions,
        "claims": claims,
        "unsupported_claims": unsupported_claims,
        "next_actions": _next_actions(dimensions, unsupported_claims),
        "boundaries": [
            "本报告仅检查本地仓库中可见的交付证据。",
            "业务承诺状态仅表示引用路径存在，不代表证据内容已被独立验证。",
            "未运行生产环境，不能证明真实流量、稳定性或客户验收。",
            "本报告不是安全审计、渗透测试或法律保证。",
        ],
    }


def write_delivery_audit_artifacts(report: dict[str, Any], output_dir: str | Path) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output / "delivery-audit.json",
        "markdown": output / "delivery-audit.md",
        "html": output / "delivery-audit.html",
        "content_brief": output / "content-brief.md",
        "content_candidates_json": output / "content-candidates.json",
        "content_candidates_markdown": output / "content-candidates.md",
        "wiki_capsule": output / "wiki-capsule.json",
    }
    paths["json"].write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths["markdown"].write_text(render_delivery_markdown(report), encoding="utf-8")
    paths["html"].write_text(render_delivery_html(report), encoding="utf-8")
    paths["content_brief"].write_text(render_content_brief(report), encoding="utf-8")
    candidate = build_content_candidate(report)
    paths["content_candidates_json"].write_text(
        json.dumps({"candidates": [candidate]}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    paths["content_candidates_markdown"].write_text(
        "# 候选选题池\n\n## 候选项\n\n" + render_content_candidate_entry(candidate),
        encoding="utf-8",
    )
    paths["wiki_capsule"].write_text(
        json.dumps(build_wiki_capsule(report, candidate), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return paths


def render_delivery_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# AI 应用交付验收报告",
        "",
        f"- 项目：{report['project_name']}",
        f"- 结论：{_status_label(report['overall_status'])}",
        f"- 证据完整度：{report['evidence_score']}%",
        "",
        "## 验收维度",
        "",
    ]
    for dimension in report["dimensions"]:
        lines.extend(
            [
                f"### {dimension['label']}：{_status_label(dimension['status'])}",
                "",
                dimension["summary"],
                "",
            ]
        )
        lines.extend(f"- `{path}`" for path in dimension["evidence"])
        if not dimension["evidence"]:
            lines.append("- 未发现可核对文件。")
        lines.append("")
    lines.extend(["## 承诺核对", ""])
    if not report["claims"]:
        lines.append("- 未提供验收承诺清单，无法判断业务功能是否达到约定。")
    for claim in report["claims"]:
        lines.append(f"- {_status_label(claim['status'])}：{claim['claim']}")
    lines.extend(["", "## 下一步", ""])
    lines.extend(f"- {action}" for action in report["next_actions"])
    lines.extend(["", "## 报告边界", ""])
    lines.extend(f"- {boundary}" for boundary in report["boundaries"])
    return "\n".join(lines).rstrip() + "\n"


def render_delivery_html(report: dict[str, Any]) -> str:
    cards = "".join(
        f"<section class='card'><div class='row'><h2>{html.escape(item['label'])}</h2>"
        f"<span class='badge {item['status'].lower()}'>{html.escape(_status_label(item['status']))}</span></div>"
        f"<p>{html.escape(item['summary'])}</p></section>"
        for item in report["dimensions"]
    )
    actions = "".join(f"<li>{html.escape(action)}</li>" for action in report["next_actions"])
    boundaries = "".join(f"<li>{html.escape(item)}</li>" for item in report["boundaries"])
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI 应用交付验收报告</title><style>
body{{margin:0;background:#f4f1ea;color:#17221c;font:16px/1.6 system-ui,"Microsoft YaHei",sans-serif}}main{{max-width:900px;margin:auto;padding:48px 20px 72px}}header{{background:#173f35;color:#fff;padding:36px;border-radius:20px}}h1{{margin:0 0 12px;font-size:34px}}.score{{font-size:54px;font-weight:800}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin:24px 0}}.card{{background:#fff;padding:22px;border:1px solid #d9d5ca;border-radius:16px}}.row{{display:flex;gap:12px;align-items:center;justify-content:space-between}}h2{{font-size:19px;margin:0}}.badge{{font-size:12px;font-weight:700;padding:5px 9px;border-radius:999px;background:#e8e4da}}.supported{{background:#d9f2e3;color:#17603b}}.partial{{background:#fff0c7;color:#7c5800}}.missing,.unverified{{background:#f9d8d2;color:#842b20}}.panel{{background:#fff;padding:24px;border-radius:16px;margin-top:16px}}small{{opacity:.78}}</style></head>
<body><main><header><small>{html.escape(report['project_name'])}</small><h1>AI 应用交付验收报告</h1><div class="score">{report['evidence_score']}%</div><p>{html.escape(_status_label(report['overall_status']))}</p></header>
<div class="grid">{cards}</div><section class="panel"><h2>优先动作</h2><ol>{actions}</ol></section>
<section class="panel"><h2>报告边界</h2><ul>{boundaries}</ul></section></main></body></html>"""


def render_content_brief(report: dict[str, Any]) -> str:
    missing = [item["label"] for item in report["dimensions"] if item["status"] != "SUPPORTED"]
    gap = "、".join(missing) if missing else "没有明显的仓库证据缺口"
    return f"""# 脱敏内容实验简报

> 本文件不含客户名称、源码、路径或凭据，可作为 Cheat on Content 的候选选题输入。

## 候选选题

- 类型：AI 应用交付避坑
- 开头：开发说“已经做完”不等于你可以付尾款，先看这 5 类证据。
- 核心事实：一次本地交付审计的证据完整度为 {report['evidence_score']}%，主要缺口是 {gap}。
- 观点：验收不是问“能不能跑”，而是把每一项承诺绑定到可重复核对的证据。
- 行动：领取付款前验收清单；有待验收项目可申请 999 元交付验真快检。

## 发布前约束

- 不宣称该项目存在安全漏洞。
- 不展示客户身份、源码、文件路径或业务数据。
- 不把仓库证据完整度描述成生产稳定性。
- 发布前进入 Cheat on Content 的盲预测流程，T+3 天回填播放、互动、咨询和付费数据。
"""


def build_content_candidate(report: dict[str, Any]) -> dict[str, Any]:
    gaps = [item["label"] for item in report["dimensions"] if item["status"] != "SUPPORTED"]
    gap_text = "、".join(gaps) if gaps else "未发现明显仓库证据缺口"
    title = f"AI 应用交付验真：{report['evidence_score']}% 证据完整度，主要缺口是{gap_text}"
    snapshot = (
        f"一次本地 AI 应用交付审计得到 {report['evidence_score']}% 的证据完整度。"
        f"主要缺口：{gap_text}。"
        "仓库证据只能支持实现、测试、部署文档等本地结论，不能证明生产稳定性或客户价值。"
        "适合用来解释付款前如何把开发承诺绑定到可重复核对的证据。"
    )
    source = "audit:reviewflow"
    return {
        "id": _candidate_id(source, title),
        "title": title,
        "source": source,
        "snapshot_text": snapshot,
        "snapshot_at": report["evidence_snapshot_at"],
        "url": None,
        "tier": None,
        "read_status": "unread",
        "category": "AI应用交付验收",
        "composite_score": None,
        "dimension_scores": None,
        "scored_under_rubric_version": None,
        "predicted_bucket": None,
        "predicted_reason": None,
        "note": "发布前不得展示客户身份、源码、路径或业务数据。",
    }


def render_content_candidate_entry(candidate: dict[str, Any]) -> str:
    return (
        f"### {candidate['title']}\n\n"
        f"- **id**: {candidate['id']}\n"
        f"- **source**: {candidate['source']}\n"
        f"- **snapshot_at**: {candidate['snapshot_at']}\n"
        f"- **tier**: \n"
        f"- **read_status**: {candidate['read_status']}\n"
        f"- **category**: {candidate['category']}\n"
        f"- **note**: {candidate['note']}\n\n"
        f"> {candidate['snapshot_text']}\n"
    )


def sync_content_candidate(report: dict[str, Any], content_project: str | Path) -> bool:
    project = Path(content_project).resolve()
    if not project.is_dir() or not (project / ".cheat-state.json").is_file():
        raise ValueError("Target is not an initialized Cheat on Content project.")
    candidate = build_content_candidate(report)
    candidates_path = project / "candidates.md"
    existing = candidates_path.read_text(encoding="utf-8") if candidates_path.exists() else "# 候选选题池\n\n## 候选项\n"
    if f"**id**: {candidate['id']}" in existing:
        return False
    separator = "\n" if existing.endswith("\n") else "\n\n"
    candidates_path.write_text(existing + separator + render_content_candidate_entry(candidate), encoding="utf-8")
    return True


def build_wiki_capsule(report: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "capsule_type": "reviewflow_delivery_audit",
        "source_audit_id": candidate["id"],
        "observed_facts": [
            f"本地仓库证据完整度为 {report['evidence_score']}%。",
            *[f"{item['label']}：{_status_label(item['status'])}。" for item in report["dimensions"]],
        ],
        "inferences": ["该项目可进入人工验收的程度由证据完整度决定，不等于生产可用。"],
        "unknowns": ["真实生产稳定性", "真实用户接受度", "内容发布表现", "付费转化"],
        "candidate_rules": [
            {
                "status": "candidate",
                "rule": "仓库证据、内容表现和付费转化必须作为三类独立证据记录。",
                "promotion_gate": "至少跨两个真实案例成立，并且没有相反证据。",
            }
        ],
        "routing": {
            "update_existing_project": True,
            "update_existing_workflow": True,
            "auto_activate_rule": False,
        },
    }


def _inventory_paths(root: Path) -> list[str]:
    paths: list[str] = []
    for current, directories, files in os.walk(root):
        directories[:] = sorted(item for item in directories if item not in SKIP_DIRECTORIES)
        current_path = Path(current)
        for filename in sorted(files):
            relative = (current_path / filename).relative_to(root).as_posix()
            if not _looks_secret(relative):
                paths.append(relative)
    return paths


def _evidence_snapshot_at(root: Path, relative_paths: list[str]) -> str:
    timestamps = [(root / path).stat().st_mtime for path in relative_paths]
    timestamp = max(timestamps, default=root.stat().st_mtime)
    return datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="seconds")


def _candidate_id(source: str, title: str, url: str | None = None) -> str:
    normalized_title = title.strip().lower().replace(" ", "")
    url_path = url.split("?")[0].rstrip("/") if url else ""
    raw = f"{source.split(':')[0]}|{normalized_title}|{url_path}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _load_claims(root: Path, evidence_path: str | Path | None, known_paths: set[str]) -> list[dict[str, Any]]:
    if evidence_path is None:
        return []
    path = Path(evidence_path)
    if _looks_secret(path.name):
        raise ValueError("Evidence manifest filename looks sensitive and will not be opened.")
    data = json.loads(path.read_text(encoding="utf-8"))
    claims = []
    for item in data.get("claims", []):
        claim = str(item.get("claim", "")).strip()
        evidence_paths = [str(value).replace("\\", "/") for value in item.get("evidence_paths", [])]
        existing = [value for value in evidence_paths if value in known_paths and _inside_root(root, value)]
        status = "SUPPORTED" if claim and evidence_paths and len(existing) == len(evidence_paths) else "UNVERIFIED"
        if claim:
            claims.append({"claim": claim, "status": status, "evidence_paths": existing})
    return claims


def _dimension(key: str, label: str, status: str, evidence: list[str], summary: str) -> dict[str, Any]:
    return {"key": key, "label": label, "status": status, "evidence": evidence, "summary": summary}


def _acceptance_dimension(claims: list[dict[str, Any]]) -> dict[str, Any]:
    supported = [claim for claim in claims if claim["status"] == "SUPPORTED"]
    status = "SUPPORTED" if claims and len(supported) == len(claims) else "PARTIAL" if supported else "UNVERIFIED"
    return _dimension(
        "acceptance",
        "业务验收",
        status,
        [path for claim in supported for path in claim["evidence_paths"]][:8],
        f"{len(supported)}/{len(claims)} 项业务承诺具备仓库内证据。" if claims else "未提供业务承诺与验收证据。",
    )


def _overall_status(score: int, dimensions: list[dict[str, Any]], unsupported: list[dict[str, Any]]) -> str:
    if score >= 80 and not unsupported and all(item["status"] != "MISSING" for item in dimensions):
        return "READY_FOR_ACCEPTANCE"
    if unsupported or any(item["status"] in {"MISSING", "UNVERIFIED"} for item in dimensions):
        return "NEEDS_EVIDENCE"
    return "REVIEW_REQUIRED"


def _next_actions(dimensions: list[dict[str, Any]], unsupported: list[dict[str, Any]]) -> list[str]:
    actions = []
    messages = {
        "implementation": "补齐可运行入口和依赖清单，并记录一次从零启动过程。",
        "tests": "为核心付费流程补自动化测试，并保存可重复执行的结果。",
        "delivery": "补 CI 与部署配置，记录回滚和健康检查方式。",
        "documentation": "补安装、配置、验收和接手说明。",
        "acceptance": "把每项业务承诺写入 evidence manifest，并绑定仓库内证据。",
    }
    for item in dimensions:
        if item["status"] != "SUPPORTED":
            actions.append(messages[item["key"]])
    if unsupported:
        actions.insert(0, f"优先核对 {len(unsupported)} 项缺少证据的交付承诺，再决定付款或上线。")
    return actions or ["保持现有证据，并进行真实环境与最终用户验收。"]


def _matching_paths(paths: list[str], predicate: Any) -> list[str]:
    return [path for path in paths if predicate(path)]


def _is_test_path(path: str) -> bool:
    lowered = path.lower()
    name = Path(lowered).name
    return lowered.startswith("tests/") or "/tests/" in lowered or name.startswith("test_") or ".test." in name or ".spec." in name


def _is_documentation_path(path: str) -> bool:
    lowered = path.lower()
    return Path(lowered).suffix in {".md", ".rst"} and ("/docs/" in f"/{lowered}" or Path(lowered).name.startswith("readme"))


def _has_readme(paths: list[str]) -> bool:
    return any(Path(path).name.lower().startswith("readme") for path in paths)


def _looks_secret(path: str) -> bool:
    lowered = path.lower()
    return any(part in lowered for part in SECRET_NAME_PARTS)


def _inside_root(root: Path, relative_path: str) -> bool:
    try:
        (root / relative_path).resolve().relative_to(root)
        return True
    except ValueError:
        return False


def _status_score(status: str) -> float:
    return {"SUPPORTED": 1.0, "PARTIAL": 0.5, "MISSING": 0.0, "UNVERIFIED": 0.0}.get(status, 0.0)


def _status_label(status: str) -> str:
    return {
        "SUPPORTED": "有证据",
        "PARTIAL": "证据不完整",
        "MISSING": "缺失",
        "UNVERIFIED": "未验证",
        "READY_FOR_ACCEPTANCE": "可进入人工验收",
        "NEEDS_EVIDENCE": "需要补证据",
        "REVIEW_REQUIRED": "需要人工复核",
    }.get(status, status)
