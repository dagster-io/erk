"""Tests for FakeClaudeCLIExecutor.

These are Layer 1 tests that verify the test double itself works correctly.
"""

from pathlib import Path

import pytest
from erk_shared.integrations.ai.abc import CommitMessageResult
from erk_shared.integrations.ai.fake import FakeClaudeCLIExecutor, GenerateCommitMessageCall


class TestFakeAIExecutor:
    """Test FakeClaudeCLIExecutor behavior."""

    def test_returns_configured_response(self) -> None:
        """FakeClaudeCLIExecutor returns the title and body configured at construction."""
        fake = FakeClaudeCLIExecutor(title="Test Title", body="Test Body")

        result = fake.generate_commit_message(
            diff_file=Path("/tmp/diff.txt"),
            repo_root=Path("/repo"),
            current_branch="feature",
            parent_branch="main",
        )

        assert result == CommitMessageResult(title="Test Title", body="Test Body")

    def test_tracks_calls(self) -> None:
        """FakeClaudeCLIExecutor tracks all calls for assertion."""
        fake = FakeClaudeCLIExecutor()

        fake.generate_commit_message(
            diff_file=Path("/tmp/diff1.txt"),
            repo_root=Path("/repo1"),
            current_branch="feature1",
            parent_branch="main",
        )
        fake.generate_commit_message(
            diff_file=Path("/tmp/diff2.txt"),
            repo_root=Path("/repo2"),
            current_branch="feature2",
            parent_branch="develop",
        )

        assert fake.call_count == 2
        assert len(fake.generate_commit_message_calls) == 2
        assert fake.generate_commit_message_calls[0] == GenerateCommitMessageCall(
            diff_file=Path("/tmp/diff1.txt"),
            repo_root=Path("/repo1"),
            current_branch="feature1",
            parent_branch="main",
        )
        assert fake.generate_commit_message_calls[1] == GenerateCommitMessageCall(
            diff_file=Path("/tmp/diff2.txt"),
            repo_root=Path("/repo2"),
            current_branch="feature2",
            parent_branch="develop",
        )

    def test_raises_configured_exception(self) -> None:
        """FakeClaudeCLIExecutor raises the exception configured at construction."""
        error = RuntimeError("AI service unavailable")
        fake = FakeClaudeCLIExecutor(should_raise=error)

        with pytest.raises(RuntimeError, match="AI service unavailable"):
            fake.generate_commit_message(
                diff_file=Path("/tmp/diff.txt"),
                repo_root=Path("/repo"),
                current_branch="feature",
                parent_branch="main",
            )

        # Call is still tracked even when raising
        assert fake.call_count == 1

    def test_default_values(self) -> None:
        """FakeClaudeCLIExecutor has sensible defaults."""
        fake = FakeClaudeCLIExecutor()

        result = fake.generate_commit_message(
            diff_file=Path("/tmp/diff.txt"),
            repo_root=Path("/repo"),
            current_branch="feature",
            parent_branch="main",
        )

        assert result.title == "Test PR title"
        assert result.body == "Test PR body"
