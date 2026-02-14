"""Unit tests for erk docs check command.

Tests use FakeAgentDocs to avoid subprocess calls (prettier).
Tests that reach Phase 2 (sync check) with real prettier belong in
tests/integration/test_docs_check.py.
"""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.context.testing import context_for_test
from erk_shared.gateway.agent_docs.fake import FakeAgentDocs

VALID_DOC = """\
---
title: Test Document
read_when:
  - editing test code
---

# Test Document
"""

INVALID_DOC = """\
---
title: ""
---

Missing read_when.
"""


def test_check_exits_zero_when_no_docs_dir() -> None:
    """Check exits 0 when docs/learned/ doesn't exist."""
    agent_docs = FakeAgentDocs(has_docs_dir=False)
    ctx = context_for_test(agent_docs=agent_docs)

    runner = CliRunner()
    result = runner.invoke(cli, ["docs", "check"], obj=ctx)

    assert result.exit_code == 0
    assert "No docs/learned/ directory found" in result.output


def test_check_exits_zero_when_no_doc_files() -> None:
    """Check exits 0 when docs/learned/ exists but has no doc files."""
    agent_docs = FakeAgentDocs(files={"index.md": "# Root Index"})
    ctx = context_for_test(agent_docs=agent_docs)

    runner = CliRunner()
    result = runner.invoke(cli, ["docs", "check"], obj=ctx)

    assert result.exit_code == 0
    assert "No agent documentation files found" in result.output


def test_check_fails_with_invalid_frontmatter() -> None:
    """Check fails when a doc has invalid frontmatter."""
    agent_docs = FakeAgentDocs(
        files={
            "bad.md": INVALID_DOC,
            "tripwires-index.md": "<!-- AUTO-GENERATED FILE -->\n# Index\n",
        }
    )
    ctx = context_for_test(agent_docs=agent_docs)

    runner = CliRunner()
    result = runner.invoke(cli, ["docs", "check"], obj=ctx)

    assert result.exit_code == 1
    assert "FAILED" in result.output


def test_check_passes_with_valid_docs_in_sync() -> None:
    """Check passes when all docs valid and generated files in sync."""
    agent_docs = FakeAgentDocs(
        files={
            "doc.md": VALID_DOC,
            "tripwires-index.md": "<!-- AUTO-GENERATED FILE -->\n# Tripwires Index\n",
        }
    )
    ctx = context_for_test(agent_docs=agent_docs)

    # Pre-sync so generated files match
    from erk.agent_docs.operations import sync_agent_docs

    sync_agent_docs(agent_docs, ctx.repo_root, dry_run=False)

    runner = CliRunner()
    result = runner.invoke(cli, ["docs", "check"], obj=ctx)

    assert result.exit_code == 0
    assert "PASSED" in result.output


def test_check_fails_when_sync_out_of_date() -> None:
    """Check fails when generated files need updating."""
    agent_docs = FakeAgentDocs(
        files={
            "architecture/doc1.md": VALID_DOC,
            "architecture/doc2.md": VALID_DOC,
        }
    )
    ctx = context_for_test(agent_docs=agent_docs)

    runner = CliRunner()
    result = runner.invoke(cli, ["docs", "check"], obj=ctx)

    assert result.exit_code == 1
    assert "out of sync" in result.output or "FAILED" in result.output
