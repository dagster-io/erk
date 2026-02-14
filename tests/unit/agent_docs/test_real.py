"""Layer 4 tests for RealAgentDocs filesystem operations.

Tests use tmp_path for real filesystem I/O. format_markdown is excluded
because it requires a prettier subprocess (covered in integration tests).
"""

from pathlib import Path

from erk.agent_docs.real import RealAgentDocs


def test_has_docs_dir_true_when_exists(tmp_path: Path) -> None:
    (tmp_path / "docs" / "learned").mkdir(parents=True)
    agent_docs = RealAgentDocs()
    assert agent_docs.has_docs_dir(tmp_path) is True


def test_has_docs_dir_false_when_missing(tmp_path: Path) -> None:
    agent_docs = RealAgentDocs()
    assert agent_docs.has_docs_dir(tmp_path) is False


def test_has_docs_dir_false_when_file_not_dir(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "learned").write_text("not a directory", encoding="utf-8")
    agent_docs = RealAgentDocs()
    assert agent_docs.has_docs_dir(tmp_path) is False


def test_list_files_returns_sorted_relative_paths(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs" / "learned"
    (docs_dir / "b").mkdir(parents=True)
    (docs_dir / "a").mkdir(parents=True)
    (docs_dir / "b" / "doc.md").write_text("# B", encoding="utf-8")
    (docs_dir / "a" / "doc.md").write_text("# A", encoding="utf-8")
    (docs_dir / "root.md").write_text("# Root", encoding="utf-8")

    agent_docs = RealAgentDocs()
    result = agent_docs.list_files(tmp_path)

    assert result == ["a/doc.md", "b/doc.md", "root.md"]


def test_list_files_returns_empty_when_no_dir(tmp_path: Path) -> None:
    agent_docs = RealAgentDocs()
    assert agent_docs.list_files(tmp_path) == []


def test_list_files_only_returns_md_files(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs" / "learned"
    docs_dir.mkdir(parents=True)
    (docs_dir / "doc.md").write_text("# Doc", encoding="utf-8")
    (docs_dir / "notes.txt").write_text("notes", encoding="utf-8")
    (docs_dir / "data.json").write_text("{}", encoding="utf-8")

    agent_docs = RealAgentDocs()
    assert agent_docs.list_files(tmp_path) == ["doc.md"]


def test_read_file_returns_content(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs" / "learned"
    docs_dir.mkdir(parents=True)
    (docs_dir / "doc.md").write_text("# Hello World", encoding="utf-8")

    agent_docs = RealAgentDocs()
    assert agent_docs.read_file(tmp_path, "doc.md") == "# Hello World"


def test_read_file_returns_none_for_missing(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs" / "learned"
    docs_dir.mkdir(parents=True)

    agent_docs = RealAgentDocs()
    assert agent_docs.read_file(tmp_path, "missing.md") is None


def test_write_file_creates_file_and_parents(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs" / "learned"
    docs_dir.mkdir(parents=True)

    agent_docs = RealAgentDocs()
    agent_docs.write_file(tmp_path, "new_category/doc.md", "# New Doc")

    file_path = docs_dir / "new_category" / "doc.md"
    assert file_path.exists()
    assert file_path.read_text(encoding="utf-8") == "# New Doc"


def test_write_file_overwrites_existing(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs" / "learned"
    docs_dir.mkdir(parents=True)
    (docs_dir / "doc.md").write_text("old content", encoding="utf-8")

    agent_docs = RealAgentDocs()
    agent_docs.write_file(tmp_path, "doc.md", "new content")

    assert (docs_dir / "doc.md").read_text(encoding="utf-8") == "new content"
