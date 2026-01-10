"""Tests for sync status display helper functions.

Layer 3 (pure unit) tests for format_sync_status - no dependencies.
Layer 4 (business logic over fakes) tests for display_sync_status.
"""

import sys
from io import StringIO
from pathlib import Path

from erk.cli.commands.checkout_helpers import (
    _is_bot_author,
    display_sync_status,
    format_sync_status,
)
from erk.core.context import ErkContext
from erk_shared.git.fake import FakeGit


class TestFormatSyncStatus:
    """Pure unit tests for format_sync_status (Layer 3 - no dependencies)."""

    def test_in_sync_returns_none(self) -> None:
        """When ahead=0 and behind=0, returns None (in sync)."""
        result = format_sync_status(ahead=0, behind=0)
        assert result is None

    def test_ahead_only(self) -> None:
        """When only ahead, returns N arrow-up format."""
        result = format_sync_status(ahead=3, behind=0)
        assert result == "3↑"

    def test_behind_only(self) -> None:
        """When only behind, returns N arrow-down format."""
        result = format_sync_status(ahead=0, behind=2)
        assert result == "2↓"

    def test_diverged_shows_both(self) -> None:
        """When both ahead and behind, shows both with space separator."""
        result = format_sync_status(ahead=1, behind=3)
        assert result == "1↑ 3↓"

    def test_single_commit_ahead(self) -> None:
        """Single commit ahead shows 1↑."""
        result = format_sync_status(ahead=1, behind=0)
        assert result == "1↑"

    def test_single_commit_behind(self) -> None:
        """Single commit behind shows 1↓."""
        result = format_sync_status(ahead=0, behind=1)
        assert result == "1↓"


class TestIsBotAuthor:
    """Pure unit tests for _is_bot_author (Layer 3 - no dependencies)."""

    def test_github_actions_bot(self) -> None:
        """Detects github-actions[bot] as a bot."""
        assert _is_bot_author("github-actions[bot]") is True

    def test_dependabot(self) -> None:
        """Detects dependabot[bot] as a bot."""
        assert _is_bot_author("dependabot[bot]") is True

    def test_generic_bot(self) -> None:
        """Detects any author with [bot] suffix."""
        assert _is_bot_author("some-service[bot]") is True

    def test_case_insensitive(self) -> None:
        """Bot detection is case insensitive."""
        assert _is_bot_author("GitHub-Actions[BOT]") is True

    def test_human_author(self) -> None:
        """Human authors are not detected as bots."""
        assert _is_bot_author("John Doe") is False

    def test_bot_in_name_without_brackets(self) -> None:
        """Author named 'bot' without brackets is not a bot."""
        assert _is_bot_author("bot") is False
        assert _is_bot_author("robotics-team") is False


class TestDisplaySyncStatus:
    """Tests for display_sync_status over fakes (Layer 4)."""

    def _make_context(self, *, ahead: int, behind: int, cwd: Path) -> ErkContext:
        """Create a minimal ErkContext with FakeGit configured for sync status."""
        git = FakeGit(
            ahead_behind={(cwd, "feature"): (ahead, behind)},
        )
        return ErkContext.for_test(git=git, cwd=cwd)

    def test_script_mode_suppresses_output(self, tmp_path: Path) -> None:
        """In script mode, no output is produced regardless of sync status."""
        ctx = self._make_context(ahead=5, behind=3, cwd=tmp_path)

        captured = StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured

        try:
            display_sync_status(ctx, worktree_path=tmp_path, branch="feature", script=True)
        finally:
            sys.stderr = old_stderr

        assert captured.getvalue() == ""

    def test_in_sync_no_output(self, tmp_path: Path) -> None:
        """When in sync, no output is produced."""
        ctx = self._make_context(ahead=0, behind=0, cwd=tmp_path)

        captured = StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured

        try:
            display_sync_status(ctx, worktree_path=tmp_path, branch="feature", script=False)
        finally:
            sys.stderr = old_stderr

        assert captured.getvalue() == ""

    def test_ahead_shows_unpushed_message(self, tmp_path: Path) -> None:
        """When ahead, shows unpushed commits message."""
        ctx = self._make_context(ahead=2, behind=0, cwd=tmp_path)

        captured = StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured

        try:
            display_sync_status(ctx, worktree_path=tmp_path, branch="feature", script=False)
        finally:
            sys.stderr = old_stderr

        output = captured.getvalue()
        assert "2↑" in output
        assert "ahead of origin" in output
        assert "unpushed" in output

    def test_ahead_singular_commit_word(self, tmp_path: Path) -> None:
        """When 1 commit ahead, uses singular 'commit' not 'commits'."""
        ctx = self._make_context(ahead=1, behind=0, cwd=tmp_path)

        captured = StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured

        try:
            display_sync_status(ctx, worktree_path=tmp_path, branch="feature", script=False)
        finally:
            sys.stderr = old_stderr

        output = captured.getvalue()
        assert "1 unpushed commit)" in output
        assert "commits" not in output

    def test_behind_shows_pull_message(self, tmp_path: Path) -> None:
        """When behind, shows git pull suggestion."""
        ctx = self._make_context(ahead=0, behind=3, cwd=tmp_path)

        captured = StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured

        try:
            display_sync_status(ctx, worktree_path=tmp_path, branch="feature", script=False)
        finally:
            sys.stderr = old_stderr

        output = captured.getvalue()
        assert "3↓" in output
        assert "behind origin" in output
        assert "git pull" in output

    def test_diverged_shows_warning(self, tmp_path: Path) -> None:
        """When diverged (both ahead and behind), shows warning with instructions."""
        ctx = self._make_context(ahead=1, behind=3, cwd=tmp_path)

        captured = StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured

        try:
            display_sync_status(ctx, worktree_path=tmp_path, branch="feature", script=False)
        finally:
            sys.stderr = old_stderr

        output = captured.getvalue()
        assert "diverged" in output
        assert "1↑ 3↓" in output
        assert "git fetch" in output or "git reset" in output

    def test_behind_with_bot_commits_shows_autofix_message(self, tmp_path: Path) -> None:
        """When behind with bot commits, shows autofix message."""
        git = FakeGit(
            ahead_behind={(tmp_path, "feature"): (0, 2)},
            behind_commit_authors={(tmp_path, "feature"): ["github-actions[bot]", "John Doe"]},
        )
        ctx = ErkContext.for_test(git=git, cwd=tmp_path)

        captured = StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured

        try:
            display_sync_status(ctx, worktree_path=tmp_path, branch="feature", script=False)
        finally:
            sys.stderr = old_stderr

        output = captured.getvalue()
        assert "2↓" in output
        assert "behind origin" in output
        assert "autofix" in output
        assert "git pull" not in output

    def test_behind_with_only_human_commits_shows_pull_message(self, tmp_path: Path) -> None:
        """When behind with only human commits, shows git pull message."""
        git = FakeGit(
            ahead_behind={(tmp_path, "feature"): (0, 1)},
            behind_commit_authors={(tmp_path, "feature"): ["John Doe"]},
        )
        ctx = ErkContext.for_test(git=git, cwd=tmp_path)

        captured = StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured

        try:
            display_sync_status(ctx, worktree_path=tmp_path, branch="feature", script=False)
        finally:
            sys.stderr = old_stderr

        output = captured.getvalue()
        assert "1↓" in output
        assert "behind origin" in output
        assert "git pull" in output
        assert "autofix" not in output
