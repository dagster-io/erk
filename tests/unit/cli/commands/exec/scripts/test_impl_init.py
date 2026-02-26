"""Tests for impl-init kit CLI command.

Tests the initialization and validation for /erk:plan-implement.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.impl_init import (
    _extract_related_docs,
    impl_init,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.impl_folder import create_impl_folder

BRANCH = "feature/test-branch"
"""Test branch name used across tests."""


def _make_ctx(tmp_path: Path, *, branch: str = BRANCH) -> ErkContext:
    """Create test ErkContext with FakeGit configured for the given branch."""
    return ErkContext.for_test(
        cwd=tmp_path,
        git=FakeGit(current_branches={tmp_path: branch}),
    )


def test_impl_init_returns_valid_json(tmp_path: Path) -> None:
    """Test impl-init returns valid JSON with expected structure."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    (impl_dir / "plan.md").write_text("# Test Plan\n\n1. Step one\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(impl_init, ["--json"], obj=_make_ctx(tmp_path))

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert data["impl_type"] == "impl"
    assert data["has_plan_tracking"] is False


def test_impl_init_extracts_related_docs(tmp_path: Path) -> None:
    """Test impl-init extracts Related Documentation section."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
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
    (impl_dir / "plan.md").write_text(plan_content, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(impl_init, ["--json"], obj=_make_ctx(tmp_path))

    assert result.exit_code == 0
    data = json.loads(result.output)
    related_docs = data["related_docs"]

    assert "dignified-python-313" in related_docs["skills"]
    assert "fake-driven-testing" in related_docs["skills"]
    assert "docs/learned/testing/kit-cli-testing.md" in related_docs["docs"]
    assert "docs/learned/patterns.md" in related_docs["docs"]


def test_impl_init_with_issue_tracking(tmp_path: Path) -> None:
    """Test impl-init detects plan-ref.json and returns plan_number."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    (impl_dir / "plan.md").write_text("# Test Plan\n", encoding="utf-8")
    (impl_dir / "plan-ref.json").write_text(
        json.dumps(
            {
                "provider": "github",
                "plan_id": "123",
                "url": "https://github.com/org/repo/issues/123",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
                "labels": [],
                "objective_id": None,
            }
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(impl_init, ["--json"], obj=_make_ctx(tmp_path))

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["has_plan_tracking"] is True
    assert data["plan_number"] == 123


def test_impl_init_detects_branch_scoped_impl(tmp_path: Path) -> None:
    """Test impl-init detects branch-scoped .erk/impl-context/<branch>/ folder."""
    create_impl_folder(tmp_path, "# Plan\n\n1. Step one", branch_name=BRANCH, overwrite=False)

    runner = CliRunner()
    result = runner.invoke(impl_init, ["--json"], obj=_make_ctx(tmp_path))

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert data["impl_type"] == "impl-context"


def test_impl_init_errors_missing_impl_folder(tmp_path: Path) -> None:
    """Test impl-init returns JSON error when no impl folder exists."""
    runner = CliRunner()
    result = runner.invoke(impl_init, ["--json"], obj=_make_ctx(tmp_path))

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["valid"] is False
    assert data["error_type"] == "no_impl_folder"


def test_impl_init_errors_missing_plan(tmp_path: Path) -> None:
    """Test impl-init returns JSON error when plan.md is missing."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    runner = CliRunner()
    result = runner.invoke(impl_init, ["--json"], obj=_make_ctx(tmp_path))

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
