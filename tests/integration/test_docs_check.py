"""Integration tests for erk docs check command.

These tests use RealAgentDocs which calls prettier via subprocess.
They must be in tests/integration/ because they depend on prettier being installed.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.agent_docs.operations import sync_agent_docs
from erk.cli.cli import cli
from erk_shared.context.testing import context_for_test
from erk_shared.gateway.agent_docs.real import RealAgentDocs

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


def _make_context(tmp_path: Path) -> tuple:
    """Create a RealAgentDocs and test context rooted at tmp_path."""
    agent_docs = RealAgentDocs()
    ctx = context_for_test(agent_docs=agent_docs, repo_root=tmp_path)
    return agent_docs, ctx


@pytest.mark.integration
def test_check_passes_with_valid_docs_in_sync(tmp_path: Path) -> None:
    """Check passes when all docs are valid and generated files are in sync."""
    docs_dir = tmp_path / "docs" / "learned"
    docs_dir.mkdir(parents=True)
    (docs_dir / "test-doc.md").write_text(VALID_DOC, encoding="utf-8")
    (docs_dir / "tripwires-index.md").write_text(
        "<!-- AUTO-GENERATED FILE -->\n# Tripwires Index\n", encoding="utf-8"
    )

    agent_docs, ctx = _make_context(tmp_path)

    # Pre-generate index so sync check passes (calls prettier)
    sync_agent_docs(agent_docs, tmp_path, dry_run=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["docs", "check"], obj=ctx)

    assert result.exit_code == 0


@pytest.mark.integration
def test_check_fails_with_invalid_frontmatter(tmp_path: Path) -> None:
    """Check fails when a doc has invalid frontmatter."""
    docs_dir = tmp_path / "docs" / "learned"
    docs_dir.mkdir(parents=True)
    (docs_dir / "bad-doc.md").write_text(INVALID_DOC, encoding="utf-8")
    (docs_dir / "tripwires-index.md").write_text(
        "<!-- AUTO-GENERATED FILE -->\n# Tripwires Index\n", encoding="utf-8"
    )

    _, ctx = _make_context(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["docs", "check"], obj=ctx)

    assert result.exit_code == 1


@pytest.mark.integration
def test_check_fails_when_sync_out_of_date(tmp_path: Path) -> None:
    """Check fails when generated files are out of sync.

    Two valid docs in the same category trigger index generation,
    but since we don't pre-generate the index, sync detects it as out of date.
    """
    docs_dir = tmp_path / "docs" / "learned"
    category_dir = docs_dir / "testing"
    category_dir.mkdir(parents=True)

    (category_dir / "doc-one.md").write_text(VALID_DOC, encoding="utf-8")
    (category_dir / "doc-two.md").write_text(VALID_DOC, encoding="utf-8")

    (docs_dir / "tripwires-index.md").write_text(
        "<!-- AUTO-GENERATED FILE -->\n# Tripwires Index\n", encoding="utf-8"
    )

    _, ctx = _make_context(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["docs", "check"], obj=ctx)

    assert result.exit_code == 1
