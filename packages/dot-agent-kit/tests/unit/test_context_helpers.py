"""Tests for context helper functions.

Layer 3 (Pure Unit Tests): Testing getter functions in isolation.
"""

from pathlib import Path

import pytest

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.context_helpers import require_github_issues, require_repo_root


def test_require_github_issues_returns_issues_when_context_initialized() -> None:
    """Test that require_github_issues returns Issues when context is initialized."""
    from unittest.mock import MagicMock

    from erk_shared.github.issues import FakeGitHubIssues

    # Create context and mock Click context
    github_issues = FakeGitHubIssues()
    test_ctx = DotAgentContext.for_test(github_issues=github_issues)

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
    test_ctx = DotAgentContext.for_test(repo_root=custom_path)

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


def test_require_repo_root_handles_erk_context_with_repo() -> None:
    """Test that require_repo_root works with ErkContext (has repo.root)."""
    from dataclasses import dataclass
    from unittest.mock import MagicMock

    @dataclass
    class MockRepoContext:
        root: Path

    @dataclass
    class MockErkContext:
        repo: MockRepoContext

    custom_path = Path("/test/erk/repo")
    erk_ctx = MockErkContext(repo=MockRepoContext(root=custom_path))

    mock_click_ctx = MagicMock()
    mock_click_ctx.obj = erk_ctx

    # Act
    result = require_repo_root(mock_click_ctx)

    # Assert
    assert result == custom_path


def test_require_repo_root_exits_when_not_in_git_repo() -> None:
    """Test that require_repo_root exits when repo is NoRepoSentinel."""
    from dataclasses import dataclass
    from unittest.mock import MagicMock

    @dataclass
    class MockNoRepoSentinel:
        """Mock sentinel - no 'root' attribute."""

        message: str = "Not inside a git repository"

    @dataclass
    class MockErkContext:
        repo: MockNoRepoSentinel

    erk_ctx = MockErkContext(repo=MockNoRepoSentinel())

    mock_click_ctx = MagicMock()
    mock_click_ctx.obj = erk_ctx

    # Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        require_repo_root(mock_click_ctx)

    assert exc_info.value.code == 1


def test_require_repo_root_exits_when_context_missing_repo_root() -> None:
    """Test that require_repo_root exits when context has neither repo_root nor repo."""
    from dataclasses import dataclass
    from unittest.mock import MagicMock

    @dataclass
    class MockUnknownContext:
        """A context type without repo_root or repo."""

        some_other_field: str = "value"

    mock_click_ctx = MagicMock()
    mock_click_ctx.obj = MockUnknownContext()

    # Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        require_repo_root(mock_click_ctx)

    assert exc_info.value.code == 1
