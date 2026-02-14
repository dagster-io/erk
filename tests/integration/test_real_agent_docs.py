"""Integration tests for RealAgentDocs.

Tests format_markdown which calls prettier via subprocess.
"""

import pytest

from erk_shared.gateway.agent_docs.real import RealAgentDocs


@pytest.mark.integration
def test_format_markdown_normalizes_content() -> None:
    """format_markdown runs prettier and normalizes markdown."""
    agent_docs = RealAgentDocs()
    content = "# Hello\n\n\n\nExtra blank lines.\n"

    result = agent_docs.format_markdown(content)

    # Prettier collapses extra blank lines
    assert "\n\n\n\n" not in result
    assert "# Hello" in result
    assert "Extra blank lines." in result


@pytest.mark.integration
def test_format_markdown_is_idempotent() -> None:
    """Running format_markdown twice produces identical output."""
    agent_docs = RealAgentDocs()
    content = "# Title\n\n__bold__ and *italic*\n"

    first_pass = agent_docs.format_markdown(content)
    second_pass = agent_docs.format_markdown(first_pass)

    assert first_pass == second_pass
