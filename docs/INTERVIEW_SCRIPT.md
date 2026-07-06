# Interview Script

## 30-second Version

I built ReviewFlow AI, a GitHub PR pre-review pipeline. When a pull request is opened, it collects the diff, changed files, CODEOWNERS mapping, SonarQube quality signals, and dependency risk signals. Then it builds a compact review context for Codex to perform semantic review. The output is a structured risk report with findings, test suggestions, and optional patch recommendations. It does not auto-merge code; it routes the PR to the right Code Owners for final review.

## 3-minute Version

The problem I wanted to solve is that manual code review is expensive, and normal static analysis cannot fully understand business logic. So I designed ReviewFlow AI as a pre-merge review node inside CI/CD.

The workflow starts from a GitHub pull request event. The system reads PR metadata, changed files, and unified diff. Then it parses CODEOWNERS to understand module ownership. After that, it normalizes SonarQube quality signals and dependency risk signals. These deterministic results are combined with the PR diff into a compact review context.

The key design is that I do not send the entire repository to the model by default. I use a diff-first context strategy: changed files, related tests, dependency manifests, owner mapping, and CI signals are prioritized. Codex then reviews the context and returns structured findings with severity, evidence, recommendation, owner, confidence, and source.

The report is generated in JSON for machines and Markdown for PR comments. The system can also request Code Owner review, but it does not auto-merge or auto-push patches. This keeps the human approval boundary clear.

The main engineering tradeoffs are context size control, false-positive control, permissions safety, and deterministic signals versus AI reasoning. SonarQube is used for quality gates, dependency tools are used for supply-chain risks, and Codex is used for semantic reasoning, missing tests, and patch suggestions.

In the MVP demo, the offline adapter is deterministic: it flags a disabled refund authorization check, combines that with a sample dependency alert and SonarQube issue, and emits JSON plus Markdown artifacts without requiring external credentials.

## Key Highlights

- CI/CD integration.
- Diff-first context building.
- CODEOWNERS-based reviewer routing.
- SonarQube quality gate integration.
- Dependency risk integration.
- Codex semantic review.
- Structured report generation.
- Safe-by-default dry-run mode.
- Human-in-the-loop final approval.

## Tradeoffs

### Why not feed the whole repository?
Because it is costly, slow, and noisy. The MVP uses minimal sufficient context and expands only when needed.

### Why not let AI approve PRs?
Because AI can hallucinate and miss business-specific constraints. The system is a pre-review assistant, not the final authority.

### Why still use SonarQube if Codex can review code?
SonarQube provides deterministic and repeatable quality signals. Codex is better at semantic reasoning and explaining impact.

### Why keep offline stub mode?
It makes the project demoable and testable without external credentials or account-specific setup.

### How is production safety controlled?
The workflow uses `pull_request`, not `pull_request_target`; GitHub write behavior is dry-run by default; PR comments and reviewer requests require explicit configuration; and the tool never auto-merges or auto-pushes patches.
