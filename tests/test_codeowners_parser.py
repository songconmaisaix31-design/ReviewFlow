from reviewflow.codeowners_parser import owners_for_file, owners_for_files, parse_codeowners


def test_codeowners_last_matching_rule_wins() -> None:
    rules = parse_codeowners(
        """
* @global
src/ @backend
src/orders/refund.py @payments @security
"""
    )

    assert owners_for_file("src/orders/refund.py", rules) == ["@payments", "@security"]
    assert owners_for_file("src/orders/other.py", rules) == ["@backend"]
    assert owners_for_file("README.md", rules) == ["@global"]


def test_codeowners_supports_globstar() -> None:
    rules = parse_codeowners("docs/** @docs\n")

    assert owners_for_files(["docs/api/index.md", "src/app.py"], rules) == {
        "docs/api/index.md": ["@docs"],
        "src/app.py": [],
    }
