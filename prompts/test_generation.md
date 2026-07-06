# Test Generation Prompt

You are generating test suggestions for a pull request.

Input: review context JSON and review findings.

Return valid JSON only:

```json
{
  "test_suggestions": [
    {
      "file": "tests/example.test.ts",
      "title": "should reject unauthorized refund request",
      "type": "unit | integration | e2e | regression",
      "reason": "The PR changes authorization-sensitive logic.",
      "pseudo_code": "..."
    }
  ]
}
```

Rules:
- Prefer high-value tests over large generated test suites.
- Focus on changed behavior, security boundaries, error handling, and regression risk.
- Do not invent APIs that are not visible in the context.
