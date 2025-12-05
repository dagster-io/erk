"""Tests for CommitMessageGenerator."""

from pathlib import Path

from erk.core.commit_message_generator import (
    CommitMessageGenerator,
    CommitMessageRequest,
)
from tests.fakes.claude_executor import FakeClaudeExecutor


def test_generate_success(tmp_path: Path) -> None:
    """Test successful commit message generation."""
    # Arrange
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff --git a/file.py b/file.py\n-old\n+new", encoding="utf-8")

    executor = FakeClaudeExecutor(
        claude_available=True,
        simulated_prompt_output="Add new feature\n\nThis adds a new feature to the codebase.",
    )
    generator = CommitMessageGenerator(executor)

    # Act
    result = generator.generate(
        CommitMessageRequest(
            diff_file=diff_file,
            repo_root=tmp_path,
            current_branch="feature-branch",
            parent_branch="main",
        )
    )

    # Assert
    assert result.success is True
    assert result.title == "Add new feature"
    assert result.body == "This adds a new feature to the codebase."
    assert result.error_message is None

    # Verify prompt was called
    assert len(executor.prompt_calls) == 1
    assert "feature-branch" in executor.prompt_calls[0]
    assert "main" in executor.prompt_calls[0]


def test_generate_with_multiline_body(tmp_path: Path) -> None:
    """Test generation with multi-line body."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff content", encoding="utf-8")

    executor = FakeClaudeExecutor(
        claude_available=True,
        simulated_prompt_output=(
            "Refactor authentication module\n\n"
            "## Summary\n\n"
            "Restructured the auth module for better maintainability.\n\n"
            "## Files Changed\n\n"
            "- `auth.py` - Main changes\n"
            "- `tests/test_auth.py` - Updated tests"
        ),
    )
    generator = CommitMessageGenerator(executor)

    result = generator.generate(
        CommitMessageRequest(
            diff_file=diff_file,
            repo_root=tmp_path,
            current_branch="refactor",
            parent_branch="main",
        )
    )

    assert result.success is True
    assert result.title == "Refactor authentication module"
    assert "## Summary" in result.body
    assert "## Files Changed" in result.body


def test_generate_fails_when_diff_file_not_found(tmp_path: Path) -> None:
    """Test that generation fails when diff file doesn't exist."""
    executor = FakeClaudeExecutor(claude_available=True)
    generator = CommitMessageGenerator(executor)

    result = generator.generate(
        CommitMessageRequest(
            diff_file=tmp_path / "nonexistent.diff",
            repo_root=tmp_path,
            current_branch="branch",
            parent_branch="main",
        )
    )

    assert result.success is False
    assert result.title is None
    assert result.body is None
    assert "not found" in result.error_message.lower()

    # Verify no prompt was called
    assert len(executor.prompt_calls) == 0


def test_generate_fails_when_diff_file_empty(tmp_path: Path) -> None:
    """Test that generation fails when diff file is empty."""
    diff_file = tmp_path / "empty.diff"
    diff_file.write_text("", encoding="utf-8")

    executor = FakeClaudeExecutor(claude_available=True)
    generator = CommitMessageGenerator(executor)

    result = generator.generate(
        CommitMessageRequest(
            diff_file=diff_file,
            repo_root=tmp_path,
            current_branch="branch",
            parent_branch="main",
        )
    )

    assert result.success is False
    assert "empty" in result.error_message.lower()

    # Verify no prompt was called
    assert len(executor.prompt_calls) == 0


def test_generate_fails_when_executor_fails(tmp_path: Path) -> None:
    """Test that generation fails when Claude execution fails."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff content", encoding="utf-8")

    executor = FakeClaudeExecutor(
        claude_available=True,
        simulated_prompt_error="Claude CLI execution failed",
    )
    generator = CommitMessageGenerator(executor)

    result = generator.generate(
        CommitMessageRequest(
            diff_file=diff_file,
            repo_root=tmp_path,
            current_branch="branch",
            parent_branch="main",
        )
    )

    assert result.success is False
    assert result.title is None
    assert result.body is None
    assert "failed" in result.error_message.lower()


def test_generate_handles_title_only_output(tmp_path: Path) -> None:
    """Test generation when output only has a title (no body)."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff content", encoding="utf-8")

    executor = FakeClaudeExecutor(
        claude_available=True,
        simulated_prompt_output="Fix typo in README",
    )
    generator = CommitMessageGenerator(executor)

    result = generator.generate(
        CommitMessageRequest(
            diff_file=diff_file,
            repo_root=tmp_path,
            current_branch="typo-fix",
            parent_branch="main",
        )
    )

    assert result.success is True
    assert result.title == "Fix typo in README"
    assert result.body == ""


def test_generate_uses_custom_model(tmp_path: Path) -> None:
    """Test that custom model can be specified."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff content", encoding="utf-8")

    executor = FakeClaudeExecutor(
        claude_available=True,
        simulated_prompt_output="Title\n\nBody",
    )
    # Use sonnet instead of default haiku
    generator = CommitMessageGenerator(executor, model="sonnet")

    result = generator.generate(
        CommitMessageRequest(
            diff_file=diff_file,
            repo_root=tmp_path,
            current_branch="branch",
            parent_branch="main",
        )
    )

    # Should still work - model is passed to executor but FakeClaudeExecutor ignores it
    assert result.success is True
