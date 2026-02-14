"""Tests for erk docs check command (run_check function).

Tests the extracted run_check function directly with tmp_path,
no monkeypatching needed.
"""

from pathlib import Path

import pytest

from erk.agent_docs.operations import sync_agent_docs
from erk.cli.commands.docs.check import run_check

VALID_DOC = """\
---
title: Test Document
read_when:
  - editing test code
---

# Test Document

Some content.
"""

INVALID_DOC = """\
---
title: ""
---

Missing read_when field.
"""


def _setup_valid_docs(project_root: Path) -> None:
    """Create a minimal valid docs/learned/ structure."""
    docs_dir = project_root / "docs" / "learned"
    docs_dir.mkdir(parents=True)
    (docs_dir / "test-doc.md").write_text(VALID_DOC)
    (docs_dir / "tripwires-index.md").write_text(
        "<!-- AUTO-GENERATED FILE -->\n# Tripwires Index\n"
    )


def test_check_passes_with_valid_docs_in_sync(tmp_path: Path) -> None:
    """Check passes when all docs are valid and generated files are in sync."""
    _setup_valid_docs(tmp_path)
    sync_agent_docs(tmp_path, dry_run=False)

    # No SystemExit means success (exit code 0)
    run_check(tmp_path)


def test_check_exits_zero_when_no_docs_dir(tmp_path: Path) -> None:
    """Check exits 0 when docs/learned/ doesn't exist."""
    with pytest.raises(SystemExit) as exc_info:
        run_check(tmp_path)

    assert exc_info.value.code == 0


def test_check_fails_with_invalid_frontmatter(tmp_path: Path) -> None:
    """Check fails when a doc has invalid frontmatter."""
    docs_dir = tmp_path / "docs" / "learned"
    docs_dir.mkdir(parents=True)
    (docs_dir / "bad-doc.md").write_text(INVALID_DOC)
    (docs_dir / "tripwires-index.md").write_text(
        "<!-- AUTO-GENERATED FILE -->\n# Tripwires Index\n"
    )

    with pytest.raises(SystemExit) as exc_info:
        run_check(tmp_path)

    assert exc_info.value.code == 1


def test_check_fails_when_sync_out_of_date(tmp_path: Path) -> None:
    """Check fails when generated files are out of sync.

    Two valid docs in the same category trigger index generation,
    but since we don't pre-generate the index, sync detects it as out of date.
    """
    docs_dir = tmp_path / "docs" / "learned"
    category_dir = docs_dir / "testing"
    category_dir.mkdir(parents=True)

    (category_dir / "doc-one.md").write_text(VALID_DOC)
    (category_dir / "doc-two.md").write_text(VALID_DOC)

    (docs_dir / "tripwires-index.md").write_text(
        "<!-- AUTO-GENERATED FILE -->\n# Tripwires Index\n"
    )

    with pytest.raises(SystemExit) as exc_info:
        run_check(tmp_path)

    assert exc_info.value.code == 1
