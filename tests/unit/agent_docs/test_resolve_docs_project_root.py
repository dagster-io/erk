"""Tests for resolve_docs_project_root() helper.

Verifies that the resolver returns repo_root when docs_path is None,
returns the external path when configured, and raises on non-existent paths.
"""

from pathlib import Path

import click
import pytest

from erk.agent_docs.operations import resolve_docs_project_root


def test_returns_repo_root_when_docs_path_is_none() -> None:
    """Test that repo_root is returned when no docs_path configured."""
    repo_root = Path("/fake/repo")

    result = resolve_docs_project_root(repo_root=repo_root, docs_path=None)

    assert result == repo_root


def test_returns_external_path_when_configured(tmp_path: Path) -> None:
    """Test that external docs path is returned when configured and exists."""
    external_docs = tmp_path / "my-docs-repo"
    external_docs.mkdir()
    repo_root = Path("/fake/repo")

    result = resolve_docs_project_root(
        repo_root=repo_root,
        docs_path=str(external_docs),
    )

    assert result == external_docs


def test_raises_click_exception_when_path_missing() -> None:
    """Test that ClickException is raised when configured path doesn't exist."""
    repo_root = Path("/fake/repo")

    with pytest.raises(click.ClickException, match="does not exist"):
        resolve_docs_project_root(
            repo_root=repo_root,
            docs_path="/nonexistent/docs/repo",
        )
