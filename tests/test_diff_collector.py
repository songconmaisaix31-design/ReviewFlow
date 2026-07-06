from pathlib import Path

from reviewflow.diff_collector import collect_diff, parse_unified_diff


def test_parse_unified_diff_changed_files_and_added_ranges() -> None:
    diff_text = Path("examples/sample_pr_diff.patch").read_text(encoding="utf-8")

    files = parse_unified_diff(diff_text)

    assert [file.path for file in files] == ["src/orders/refund.py", "requirements.txt"]
    assert files[0].status == "modified"
    assert files[0].added_ranges == [(10, 13)]
    assert files[1].added_ranges == [(4, 4)]


def test_collect_diff_returns_context_shape() -> None:
    result = collect_diff("examples/sample_pr_diff.patch")

    assert result["changed_file_paths"] == ["src/orders/refund.py", "requirements.txt"]
    assert "raw_diff" in result
