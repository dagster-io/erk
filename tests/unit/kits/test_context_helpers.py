"""Tests for context helper functions.

Layer 3 (Pure Unit Tests): Testing getter functions in isolation.
"""

from pathlib import Path

import pytest

from erk.kits.context_helpers import require_github_issues
from erk_shared.context import ErkContext
from erk_shared.context.helpers import require_project_root, require_repo_root


def test_require_github_issues_returns_issues_when_context_initialized() -> None:
    """Test that require_github_issues returns Issues when context is initialized."""
    from unittest.mock import MagicMock

    from erk_shared.github.issues import FakeGitHubIssues

    # Create context and mock Click context
    github_issues = FakeGitHubIssues()
    test_ctx = ErkContext.for_test(github_issues=github_issues)

    mock_click_ctx = MagicMock()
    mock_click_ctx.obj = test_ctx

    # Act
    result = require_github_issues(mock_click_ctx)

    # Assert
    assert result is github_issues


def test_require_github_issues_exits_when_context_none() -> None:
    """Test that require_github_issues exits with code 1 when context is None."""
    from unittest.mock import MagicMock

    mock_click_ctx = MagicMock()
    mock_click_ctx.obj = None

    # Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        require_github_issues(mock_click_ctx)

    assert exc_info.value.code == 1


def test_require_repo_root_returns_path_when_context_initialized() -> None:
    """Test that require_repo_root returns repo_root when context is initialized."""
    from unittest.mock import MagicMock

    # Create context with custom repo_root
    custom_path = Path("/test/repo")
    test_ctx = ErkContext.for_test(repo_root=custom_path)

    mock_click_ctx = MagicMock()
    mock_click_ctx.obj = test_ctx

    # Act
    result = require_repo_root(mock_click_ctx)

    # Assert
    assert result == custom_path


def test_require_repo_root_exits_when_context_none() -> None:
    """Test that require_repo_root exits with code 1 when context is None."""
    from unittest.mock import MagicMock

    mock_click_ctx = MagicMock()
    mock_click_ctx.obj = None

    # Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        require_repo_root(mock_click_ctx)

    assert exc_info.value.code == 1


def test_require_repo_root_exits_when_not_in_git_repo() -> None:
    """Test that require_repo_root exits when repo is NoRepoSentinel."""
    from dataclasses import replace
    from unittest.mock import MagicMock

    from erk_shared.context.types import NoRepoSentinel

    # Create test context and replace repo with NoRepoSentinel
    test_ctx = ErkContext.for_test()
    test_ctx_outside_repo = replace(test_ctx, repo=NoRepoSentinel())

    mock_click_ctx = MagicMock()
    mock_click_ctx.obj = test_ctx_outside_repo

    # Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        require_repo_root(mock_click_ctx)

    assert exc_info.value.code == 1


def test_require_repo_root_exits_when_context_not_erk_context() -> None:
    """Test that require_repo_root exits when context is not ErkContext."""
    from dataclasses import dataclass
    from unittest.mock import MagicMock

    @dataclass
    class MockUnknownContext:
        """A context type that is not ErkContext."""

        some_field: str = "value"

    mock_click_ctx = MagicMock()
    mock_click_ctx.obj = MockUnknownContext()

    # Act & Assert - should fail because context is not ErkContext
    with pytest.raises(SystemExit) as exc_info:
        require_repo_root(mock_click_ctx)

    assert exc_info.value.code == 1


def test_require_project_root_returns_repo_root(tmp_path: Path) -> None:
    """Test that require_project_root returns repo_root.

    With the project system removed, require_project_root always returns repo_root.
    """
    from unittest.mock import MagicMock

    from erk_shared.git.fake import FakeGit

    # Set up directory structure
    repo_root = tmp_path / "repo"
    cwd = repo_root / "some" / "subdir"

    # Create directories
    cwd.mkdir(parents=True)

    # Create fake git with existing paths
    git = FakeGit(existing_paths={repo_root, cwd})

    test_ctx = ErkContext.for_test(repo_root=repo_root, cwd=cwd, git=git)

    mock_click_ctx = MagicMock()
    mock_click_ctx.obj = test_ctx

    # Act
    result = require_project_root(mock_click_ctx)

    # Assert - should always return repo root
    assert result == repo_root


def test_require_project_root_exits_when_context_none() -> None:
    """Test that require_project_root exits with code 1 when context is None."""
    from unittest.mock import MagicMock

    mock_click_ctx = MagicMock()
    mock_click_ctx.obj = None

    # Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        require_project_root(mock_click_ctx)

    assert exc_info.value.code == 1
