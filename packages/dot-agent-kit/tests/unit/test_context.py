"""Tests for context creation.

Layer 3 (Pure Unit Tests): Zero dependencies, testing context factory functions.
"""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.real import RealGitHubIssues

from dot_agent_kit.context import DotAgentContext, create_context


def test_create_context_returns_real_implementations() -> None:
    """Test that create_context returns production implementations."""
    ctx = create_context(debug=False)

    assert isinstance(ctx.github_issues, RealGitHubIssues)
    assert ctx.debug is False


def test_create_context_with_debug() -> None:
    """Test that debug flag is preserved."""
    ctx = create_context(debug=True)

    assert ctx.debug is True


def test_for_test_uses_fake_defaults() -> None:
    """Test that for_test() returns fake implementations by default."""
    ctx = DotAgentContext.for_test()

    assert isinstance(ctx.github_issues, FakeGitHubIssues)
    assert ctx.debug is False


def test_for_test_accepts_custom_github_issues() -> None:
    """Test that for_test() accepts custom github_issues implementation."""
    custom_issues = FakeGitHubIssues()
    ctx = DotAgentContext.for_test(github_issues=custom_issues)

    assert ctx.github_issues is custom_issues


def test_for_test_accepts_debug_flag() -> None:
    """Test that for_test() respects debug flag."""
    ctx = DotAgentContext.for_test(debug=True)

    assert ctx.debug is True


def test_context_is_frozen() -> None:
    """Test that context is immutable (frozen dataclass)."""
    ctx = DotAgentContext.for_test()

    with pytest.raises(FrozenInstanceError):
        ctx.debug = True  # type: ignore[misc]


def test_context_attributes_accessible() -> None:
    """Test that context attributes are accessible via dot notation."""
    ctx = DotAgentContext.for_test()

    # Should not raise AttributeError
    _ = ctx.github_issues
    _ = ctx.debug
    _ = ctx.repo_root


def test_context_has_repo_root_field() -> None:
    """Test that DotAgentContext has repo_root field."""
    ctx = DotAgentContext.for_test(repo_root=Path("/test/repo"))

    assert ctx.repo_root == Path("/test/repo")


def test_for_test_uses_default_repo_root() -> None:
    """Test that for_test() uses default repo_root when not provided."""
    ctx = DotAgentContext.for_test()

    assert ctx.repo_root == Path("/fake/repo")


def test_for_test_accepts_custom_repo_root() -> None:
    """Test that for_test() accepts custom repo_root."""
    custom_path = Path("/custom/path")
    ctx = DotAgentContext.for_test(repo_root=custom_path)

    assert ctx.repo_root == custom_path
