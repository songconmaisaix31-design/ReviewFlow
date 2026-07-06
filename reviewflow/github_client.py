"""Dry-run GitHub client boundary."""

from __future__ import annotations

from typing import Any


def post_pr_comment(event: dict[str, Any], body: str, config: dict[str, Any]) -> dict[str, Any]:
    github_config = config.get("github", {})
    if github_config.get("dry_run", True) or not github_config.get("comment_on_pr", False):
        return {"dry_run": True, "action": "post_pr_comment", "body_length": len(body)}
    raise NotImplementedError("Real GitHub comment posting is intentionally deferred for this MVP.")


def request_reviewers(event: dict[str, Any], reviewers: list[str], config: dict[str, Any]) -> dict[str, Any]:
    github_config = config.get("github", {})
    if github_config.get("dry_run", True) or not github_config.get("request_reviewers", False):
        return {"dry_run": True, "action": "request_reviewers", "reviewers": reviewers}
    raise NotImplementedError("Real GitHub reviewer requests are intentionally deferred for this MVP.")
