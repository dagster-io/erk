"""Layer 1 tests for PrintingAgentDocs.

Verify that read methods delegate silently and write_file prints then delegates.
"""

from pathlib import Path

from erk_shared.gateway.agent_docs.fake import FakeAgentDocs
from erk_shared.gateway.agent_docs.printing import PrintingAgentDocs

PROJECT_ROOT = Path("/fake/repo")


def test_has_docs_dir_delegates_to_wrapped() -> None:
    wrapped = FakeAgentDocs(files={}, has_docs_dir=True)
    printing = PrintingAgentDocs(wrapped)
    assert printing.has_docs_dir(PROJECT_ROOT) is True


def test_list_files_delegates_to_wrapped() -> None:
    wrapped = FakeAgentDocs(files={"a.md": "A", "b.md": "B"}, has_docs_dir=True)
    printing = PrintingAgentDocs(wrapped)
    assert printing.list_files(PROJECT_ROOT) == ["a.md", "b.md"]


def test_read_file_delegates_to_wrapped() -> None:
    wrapped = FakeAgentDocs(files={"doc.md": "# Content"}, has_docs_dir=True)
    printing = PrintingAgentDocs(wrapped)
    assert printing.read_file(PROJECT_ROOT, "doc.md") == "# Content"


def test_write_file_delegates_to_wrapped() -> None:
    wrapped = FakeAgentDocs(files={}, has_docs_dir=True)
    printing = PrintingAgentDocs(wrapped)
    printing.write_file(PROJECT_ROOT, "new.md", "# New")

    assert wrapped.written_files == {"new.md": "# New"}
    assert wrapped.read_file(PROJECT_ROOT, "new.md") == "# New"


def test_format_markdown_delegates_to_wrapped() -> None:
    wrapped = FakeAgentDocs(files={}, has_docs_dir=True)
    printing = PrintingAgentDocs(wrapped)
    content = "# Hello\n\nSome text\n"
    assert printing.format_markdown(content) == content
