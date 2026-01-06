"""Tests for impl-init kit CLI command.

Tests the initialization and validation for /erk:system:impl-execute.
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.cli.commands.exec.scripts.impl_init import (
    _extract_related_docs,
    impl_init,
)


@pytest.fixture
def impl_folder(tmp_path: Path) -> Path:
    """Create .impl/ folder with test files."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Create plan.md with Related Documentation section
    plan_content = """# Test Plan

## Objective
Build a test feature.

## Implementation Steps

1. Create module
2. Add tests
3. Update documentation

## Related Documentation

**Skills:**
- `dignified-python-313`
- `fake-driven-testing`

**Docs:**
- [Kit CLI Testing](docs/learned/testing/kit-cli-testing.md)
- `docs/learned/patterns.md`
"""
    plan_md = impl_dir / "plan.md"
    plan_md.write_text(plan_content, encoding="utf-8")

    return impl_dir


def test_impl_init_returns_valid_json(impl_folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test impl-init returns valid JSON with expected structure."""
    monkeypatch.chdir(impl_folder.parent)

    runner = CliRunner()
    result = runner.invoke(impl_init, ["--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert data["impl_type"] == "impl"
    assert data["has_issue_tracking"] is False


def test_impl_init_extracts_related_docs(
    impl_folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test impl-init extracts Related Documentation section."""
    monkeypatch.chdir(impl_folder.parent)

    runner = CliRunner()
    result = runner.invoke(impl_init, ["--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    related_docs = data["related_docs"]

    assert "dignified-python-313" in related_docs["skills"]
    assert "fake-driven-testing" in related_docs["skills"]
    assert "docs/learned/testing/kit-cli-testing.md" in related_docs["docs"]
    assert "docs/learned/patterns.md" in related_docs["docs"]


def test_impl_init_with_issue_tracking(impl_folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test impl-init detects issue.json and returns issue_number."""
    issue_json = impl_folder / "issue.json"
    issue_json.write_text(
        json.dumps(
            {
                "issue_number": 123,
                "issue_url": "https://github.com/org/repo/issues/123",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(impl_folder.parent)

    runner = CliRunner()
    result = runner.invoke(impl_init, ["--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["has_issue_tracking"] is True
    assert data["issue_number"] == 123


def test_impl_init_detects_worker_impl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test impl-init detects .worker-impl/ folder."""
    # Create .worker-impl/ folder instead of .impl/
    impl_dir = tmp_path / ".worker-impl"
    impl_dir.mkdir()

    plan_md = impl_dir / "plan.md"
    plan_md.write_text("# Plan\n\n1. Step one", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(impl_init, ["--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert data["impl_type"] == "worker-impl"


def test_impl_init_errors_missing_impl_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test impl-init returns JSON error when no impl folder exists."""
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(impl_init, ["--json"])

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["valid"] is False
    assert data["error_type"] == "no_impl_folder"


def test_impl_init_errors_missing_plan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test impl-init returns JSON error when plan.md is missing."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(impl_init, ["--json"])

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["valid"] is False
    assert data["error_type"] == "no_plan_file"


# Unit tests for helper functions


def test_extract_related_docs_skills() -> None:
    """Test _extract_related_docs extracts skills from markdown."""
    plan_content = """# Plan

## Related Documentation

**Skills:**
- `skill-one`
- `skill-two`
- `skill-three`
"""
    result = _extract_related_docs(plan_content)

    assert result["skills"] == ["skill-one", "skill-two", "skill-three"]
    assert result["docs"] == []


def test_extract_related_docs_markdown_links() -> None:
    """Test _extract_related_docs extracts markdown links."""
    plan_content = """# Plan

## Related Documentation

**Docs:**
- [Some Doc](path/to/doc.md)
- [Another Doc](another/path.md)
"""
    result = _extract_related_docs(plan_content)

    assert result["skills"] == []
    assert "path/to/doc.md" in result["docs"]
    assert "another/path.md" in result["docs"]


def test_extract_related_docs_backtick_paths() -> None:
    """Test _extract_related_docs extracts backtick-enclosed paths."""
    plan_content = """# Plan

## Related Documentation

**Docs:**
- `path/to/file.md`
- `another/file.md`
"""
    result = _extract_related_docs(plan_content)

    assert result["skills"] == []
    assert "path/to/file.md" in result["docs"]
    assert "another/file.md" in result["docs"]


def test_extract_related_docs_missing_section() -> None:
    """Test _extract_related_docs returns empty when section missing."""
    plan_content = """# Plan

## Implementation Steps

1. Do something
"""
    result = _extract_related_docs(plan_content)

    assert result == {"skills": [], "docs": []}
