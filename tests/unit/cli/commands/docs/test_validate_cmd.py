"""Unit tests for erk docs validate command.

Tests use FakeAgentDocs to avoid subprocess calls.
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


def test_validate_exits_zero_when_no_docs_dir() -> None:
    agent_docs = FakeAgentDocs(has_docs_dir=False)
    ctx = context_for_test(agent_docs=agent_docs)

    runner = CliRunner()
    result = runner.invoke(cli, ["docs", "validate"], obj=ctx)

    assert result.exit_code == 0
    assert "No docs/learned/ directory found" in result.output


def test_validate_exits_zero_when_no_doc_files() -> None:
    agent_docs = FakeAgentDocs(files={"index.md": "# Root Index"})
    ctx = context_for_test(agent_docs=agent_docs)

    runner = CliRunner()
    result = runner.invoke(cli, ["docs", "validate"], obj=ctx)

    assert result.exit_code == 0
    assert "No agent documentation files found" in result.output


def test_validate_passes_with_valid_docs() -> None:
    agent_docs = FakeAgentDocs(
        files={
            "doc.md": VALID_DOC,
            "tripwires-index.md": "<!-- AUTO-GENERATED FILE -->\n# Index\n",
        }
    )
    ctx = context_for_test(agent_docs=agent_docs)

    runner = CliRunner()
    result = runner.invoke(cli, ["docs", "validate"], obj=ctx)

    assert result.exit_code == 0
    assert "PASSED" in result.output


def test_validate_fails_with_invalid_docs() -> None:
    agent_docs = FakeAgentDocs(
        files={
            "bad.md": INVALID_DOC,
            "tripwires-index.md": "<!-- AUTO-GENERATED FILE -->\n# Index\n",
        }
    )
    ctx = context_for_test(agent_docs=agent_docs)

    runner = CliRunner()
    result = runner.invoke(cli, ["docs", "validate"], obj=ctx)

    assert result.exit_code == 1
    assert "FAILED" in result.output


def test_validate_verbose_shows_all_files() -> None:
    agent_docs = FakeAgentDocs(
        files={
            "doc.md": VALID_DOC,
            "tripwires-index.md": "<!-- AUTO-GENERATED FILE -->\n# Index\n",
        }
    )
    ctx = context_for_test(agent_docs=agent_docs)

    runner = CliRunner()
    result = runner.invoke(cli, ["docs", "validate", "--verbose"], obj=ctx)

    assert result.exit_code == 0
    assert "OK" in result.output
    assert "doc.md" in result.output
