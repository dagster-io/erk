"""Unit tests for erk docs sync command.

Tests use FakeAgentDocs to avoid subprocess calls (prettier).
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


def test_sync_exits_zero_when_no_docs_dir() -> None:
    agent_docs = FakeAgentDocs(files={}, has_docs_dir=False)
    ctx = context_for_test(agent_docs=agent_docs)

    runner = CliRunner()
    result = runner.invoke(cli, ["docs", "sync"], obj=ctx)

    assert result.exit_code == 0
    assert "No docs/learned/ directory found" in result.output


def test_sync_creates_index_files() -> None:
    agent_docs = FakeAgentDocs(has_docs_dir=True, files={"doc.md": VALID_DOC})
    ctx = context_for_test(agent_docs=agent_docs)

    runner = CliRunner()
    result = runner.invoke(cli, ["docs", "sync"], obj=ctx)

    assert result.exit_code == 0
    assert "index.md" in agent_docs.written_files


def test_sync_dry_run_does_not_write() -> None:
    agent_docs = FakeAgentDocs(has_docs_dir=True, files={"doc.md": VALID_DOC})
    ctx = context_for_test(agent_docs=agent_docs)

    runner = CliRunner()
    result = runner.invoke(cli, ["docs", "sync", "--dry-run"], obj=ctx)

    assert result.exit_code == 0
    assert agent_docs.written_files == {}
    assert "Dry run" in result.output


def test_sync_check_exits_one_when_out_of_sync() -> None:
    agent_docs = FakeAgentDocs(
        has_docs_dir=True,
        files={
            "architecture/doc1.md": VALID_DOC,
            "architecture/doc2.md": VALID_DOC,
        },
    )
    ctx = context_for_test(agent_docs=agent_docs)

    runner = CliRunner()
    result = runner.invoke(cli, ["docs", "sync", "--check"], obj=ctx)

    assert result.exit_code == 1
    assert "out of sync" in result.output


def test_sync_check_exits_zero_when_in_sync() -> None:
    agent_docs = FakeAgentDocs(has_docs_dir=True, files={"doc.md": VALID_DOC})
    ctx = context_for_test(agent_docs=agent_docs)

    # Pre-sync so files match
    from erk.agent_docs.operations import sync_agent_docs

    sync_agent_docs(agent_docs, ctx.repo_root, dry_run=False, on_progress=lambda _: None)

    runner = CliRunner()
    result = runner.invoke(cli, ["docs", "sync", "--check"], obj=ctx)

    assert result.exit_code == 0
    assert "up to date" in result.output
