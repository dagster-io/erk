"""Unit tests for erk docs check command (run_check function).

Only tests that do NOT trigger subprocess calls belong here.
Tests that reach Phase 2 (sync check) invoke prettier via subprocess
and belong in tests/integration/test_docs_check.py.
"""

from pathlib import Path

import pytest

from erk.cli.commands.docs.check import run_check


def test_check_exits_zero_when_no_docs_dir(tmp_path: Path) -> None:
    """Check exits 0 when docs/learned/ doesn't exist."""
    with pytest.raises(SystemExit) as exc_info:
        run_check(tmp_path)

    assert exc_info.value.code == 0


def test_check_exits_zero_when_no_doc_files(tmp_path: Path) -> None:
    """Check exits 0 when docs/learned/ exists but has no doc files."""
    docs_dir = tmp_path / "docs" / "learned"
    docs_dir.mkdir(parents=True)
    # Only non-doc files (index.md is skipped by discover_agent_docs)
    (docs_dir / "index.md").write_text("# Index\n")

    with pytest.raises(SystemExit) as exc_info:
        run_check(tmp_path)

    assert exc_info.value.code == 0
