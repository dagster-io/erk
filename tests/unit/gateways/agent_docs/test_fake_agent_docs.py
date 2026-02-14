"""Layer 1 tests for FakeAgentDocs.

Verify the fake implementation's state management and mutation tracking
so higher-layer tests can rely on it as a trustworthy test double.
"""

from pathlib import Path

from erk_shared.gateway.agent_docs.fake import FakeAgentDocs


def test_has_docs_dir_returns_configured_value() -> None:
    agent_docs = FakeAgentDocs(files={}, has_docs_dir=False)
    assert agent_docs.has_docs_dir(Path("/repo")) is False


def test_has_docs_dir_true() -> None:
    agent_docs = FakeAgentDocs(files={}, has_docs_dir=True)
    assert agent_docs.has_docs_dir(Path("/repo")) is True


def test_list_files_returns_sorted_keys() -> None:
    agent_docs = FakeAgentDocs(files={"b.md": "B", "a.md": "A", "c.md": "C"}, has_docs_dir=True)
    assert agent_docs.list_files(Path("/repo")) == ["a.md", "b.md", "c.md"]


def test_list_files_empty_when_no_files() -> None:
    agent_docs = FakeAgentDocs(files={}, has_docs_dir=True)
    assert agent_docs.list_files(Path("/repo")) == []


def test_read_file_returns_content() -> None:
    agent_docs = FakeAgentDocs(files={"foo.md": "# Hello"}, has_docs_dir=True)
    assert agent_docs.read_file(Path("/repo"), "foo.md") == "# Hello"


def test_read_file_returns_none_for_missing() -> None:
    agent_docs = FakeAgentDocs(files={}, has_docs_dir=True)
    assert agent_docs.read_file(Path("/repo"), "missing.md") is None


def test_write_file_updates_files_and_tracks_mutation() -> None:
    agent_docs = FakeAgentDocs(files={}, has_docs_dir=True)
    agent_docs.write_file(Path("/repo"), "new.md", "# New")

    assert agent_docs.read_file(Path("/repo"), "new.md") == "# New"
    assert agent_docs.written_files == {"new.md": "# New"}


def test_write_file_overwrites_existing() -> None:
    agent_docs = FakeAgentDocs(files={"doc.md": "old"}, has_docs_dir=True)
    agent_docs.write_file(Path("/repo"), "doc.md", "new")

    assert agent_docs.read_file(Path("/repo"), "doc.md") == "new"
    assert agent_docs.written_files == {"doc.md": "new"}


def test_written_files_returns_copy() -> None:
    agent_docs = FakeAgentDocs(files={}, has_docs_dir=True)
    agent_docs.write_file(Path("/repo"), "a.md", "content")

    copy = agent_docs.written_files
    copy["b.md"] = "injected"

    assert "b.md" not in agent_docs.written_files


def test_format_markdown_is_identity() -> None:
    agent_docs = FakeAgentDocs(files={}, has_docs_dir=True)
    content = "# Hello\n\nSome *bold* text\n"
    assert agent_docs.format_markdown(content) == content


def test_project_root_is_ignored() -> None:
    """FakeAgentDocs ignores project_root - all paths are relative keys."""
    agent_docs = FakeAgentDocs(files={"doc.md": "content"}, has_docs_dir=True)

    assert agent_docs.has_docs_dir(Path("/any/path")) is True
    assert agent_docs.read_file(Path("/different/path"), "doc.md") == "content"
    assert agent_docs.list_files(Path("/yet/another")) == ["doc.md"]
