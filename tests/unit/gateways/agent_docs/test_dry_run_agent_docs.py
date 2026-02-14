"""Layer 1 tests for DryRunAgentDocs.

Verify that read methods delegate to wrapped and write_file is a no-op.
"""

from pathlib import Path

from erk_shared.gateway.agent_docs.dry_run import DryRunAgentDocs
from erk_shared.gateway.agent_docs.fake import FakeAgentDocs

PROJECT_ROOT = Path("/fake/repo")


def test_has_docs_dir_delegates_to_wrapped() -> None:
    wrapped = FakeAgentDocs(files={}, has_docs_dir=True)
    dry_run = DryRunAgentDocs(wrapped)
    assert dry_run.has_docs_dir(PROJECT_ROOT) is True


def test_has_docs_dir_false_delegates_to_wrapped() -> None:
    wrapped = FakeAgentDocs(files={}, has_docs_dir=False)
    dry_run = DryRunAgentDocs(wrapped)
    assert dry_run.has_docs_dir(PROJECT_ROOT) is False


def test_list_files_delegates_to_wrapped() -> None:
    wrapped = FakeAgentDocs(files={"a.md": "A", "b.md": "B"}, has_docs_dir=True)
    dry_run = DryRunAgentDocs(wrapped)
    assert dry_run.list_files(PROJECT_ROOT) == ["a.md", "b.md"]


def test_read_file_delegates_to_wrapped() -> None:
    wrapped = FakeAgentDocs(files={"doc.md": "# Content"}, has_docs_dir=True)
    dry_run = DryRunAgentDocs(wrapped)
    assert dry_run.read_file(PROJECT_ROOT, "doc.md") == "# Content"


def test_read_file_returns_none_for_missing() -> None:
    wrapped = FakeAgentDocs(files={}, has_docs_dir=True)
    dry_run = DryRunAgentDocs(wrapped)
    assert dry_run.read_file(PROJECT_ROOT, "missing.md") is None


def test_write_file_does_not_write_to_wrapped() -> None:
    wrapped = FakeAgentDocs(files={}, has_docs_dir=True)
    dry_run = DryRunAgentDocs(wrapped)
    dry_run.write_file(PROJECT_ROOT, "new.md", "# New")

    assert wrapped.written_files == {}
    assert wrapped.read_file(PROJECT_ROOT, "new.md") is None


def test_format_markdown_delegates_to_wrapped() -> None:
    wrapped = FakeAgentDocs(files={}, has_docs_dir=True)
    dry_run = DryRunAgentDocs(wrapped)
    content = "# Hello\n\nSome text\n"
    assert dry_run.format_markdown(content) == content
