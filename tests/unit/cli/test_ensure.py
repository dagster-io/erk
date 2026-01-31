"""Tests for CLI Ensure utility class."""

from pathlib import Path
from unittest import mock

import pytest

from erk.cli.ensure import Ensure, UserFacingCliError
from erk_shared.context.testing import context_for_test
from erk_shared.gateway.graphite.disabled import (
    GraphiteDisabled,
    GraphiteDisabledReason,
)


class TestEnsureNotNone:
    """Tests for Ensure.not_none method."""

    def test_returns_value_when_not_none(self) -> None:
        """Ensure.not_none returns the value unchanged when not None."""
        result = Ensure.not_none("hello", "Value is None")
        assert result == "hello"

    def test_returns_value_preserves_type(self) -> None:
        """Ensure.not_none preserves the type of the returned value."""
        value: int | None = 42
        result = Ensure.not_none(value, "Value is None")
        assert result == 42
        # Type checker should infer result as int, not int | None

    def test_exits_when_none(self) -> None:
        """Ensure.not_none raises UserFacingCliError when value is None."""
        with pytest.raises(UserFacingCliError):
            Ensure.not_none(None, "Value is None")

    def test_error_message_output(self) -> None:
        """Ensure.not_none stores error message in exception."""
        with pytest.raises(UserFacingCliError) as exc_info:
            Ensure.not_none(None, "Custom error message")

        assert exc_info.value.message == "Custom error message"

    def test_works_with_complex_types(self) -> None:
        """Ensure.not_none works with complex types like dicts and lists."""
        data: dict[str, int] | None = {"key": 123}
        result = Ensure.not_none(data, "Data is None")
        assert result == {"key": 123}

    def test_zero_is_not_none(self) -> None:
        """Ensure.not_none returns 0 since 0 is not None."""
        result = Ensure.not_none(0, "Value is None")
        assert result == 0

    def test_empty_string_is_not_none(self) -> None:
        """Ensure.not_none returns empty string since empty string is not None."""
        result = Ensure.not_none("", "Value is None")
        assert result == ""

    def test_empty_list_is_not_none(self) -> None:
        """Ensure.not_none returns empty list since empty list is not None."""
        result: list[str] | None = []
        actual = Ensure.not_none(result, "Value is None")
        assert actual == []

    def test_false_is_not_none(self) -> None:
        """Ensure.not_none returns False since False is not None."""
        result = Ensure.not_none(False, "Value is None")
        assert result is False


class TestEnsureGtInstalled:
    """Tests for Ensure.gt_installed method."""

    def test_succeeds_when_gt_on_path(self) -> None:
        """Ensure.gt_installed succeeds when gt is found on PATH."""
        with mock.patch("shutil.which", return_value="/usr/local/bin/gt"):
            # Should not raise
            Ensure.gt_installed()

    def test_exits_when_gt_not_found(self) -> None:
        """Ensure.gt_installed raises UserFacingCliError when gt not on PATH."""
        with mock.patch("shutil.which", return_value=None):
            with pytest.raises(UserFacingCliError):
                Ensure.gt_installed()

    def test_error_message_includes_install_instructions(self) -> None:
        """Ensure.gt_installed stores helpful installation instructions in exception."""
        with mock.patch("shutil.which", return_value=None):
            with pytest.raises(UserFacingCliError) as exc_info:
                Ensure.gt_installed()

        assert "Graphite CLI (gt) is not installed" in exc_info.value.message
        assert "npm install -g @withgraphite/graphite-cli" in exc_info.value.message


class TestEnsureGraphiteAvailable:
    """Tests for Ensure.graphite_available method."""

    def test_succeeds_when_graphite_enabled(self) -> None:
        """Ensure.graphite_available succeeds when graphite is a real implementation."""
        # Default context_for_test provides FakeGraphite (not GraphiteDisabled)
        ctx = context_for_test()

        # Should not raise
        Ensure.graphite_available(ctx)

    def test_exits_when_config_disabled(self) -> None:
        """Ensure.graphite_available raises UserFacingCliError when disabled via config."""
        disabled = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)
        ctx = context_for_test(graphite=disabled)

        with pytest.raises(UserFacingCliError):
            Ensure.graphite_available(ctx)

    def test_exits_when_not_installed(self) -> None:
        """Ensure.graphite_available raises UserFacingCliError when gt not installed."""
        disabled = GraphiteDisabled(reason=GraphiteDisabledReason.NOT_INSTALLED)
        ctx = context_for_test(graphite=disabled)

        with pytest.raises(UserFacingCliError):
            Ensure.graphite_available(ctx)

    def test_config_disabled_error_message(self) -> None:
        """Error message for CONFIG_DISABLED includes config enable instruction."""
        disabled = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)
        ctx = context_for_test(graphite=disabled)

        with pytest.raises(UserFacingCliError) as exc_info:
            Ensure.graphite_available(ctx)

        assert "requires Graphite to be enabled" in exc_info.value.message
        assert "erk config set use_graphite true" in exc_info.value.message

    def test_not_installed_error_message(self) -> None:
        """Error message for NOT_INSTALLED includes installation instructions."""
        disabled = GraphiteDisabled(reason=GraphiteDisabledReason.NOT_INSTALLED)
        ctx = context_for_test(graphite=disabled)

        with pytest.raises(UserFacingCliError) as exc_info:
            Ensure.graphite_available(ctx)

        assert "requires Graphite to be installed" in exc_info.value.message
        assert "npm install -g @withgraphite/graphite-cli" in exc_info.value.message


class TestEnsureBranchGraphiteTrackedOrNew:
    """Tests for Ensure.branch_graphite_tracked_or_new method."""

    def test_succeeds_when_graphite_disabled(self) -> None:
        """No-op when Graphite is disabled."""
        disabled = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)
        ctx = context_for_test(graphite=disabled)
        repo_root = Path("/fake/repo")

        # Should not raise - Graphite disabled means we skip the check
        Ensure.branch_graphite_tracked_or_new(ctx, repo_root, "feature", "main")

    def test_succeeds_when_branch_does_not_exist(self) -> None:
        """No-op when branch doesn't exist locally (will be created+tracked)."""
        from erk_shared.gateway.git.fake import FakeGit
        from erk_shared.gateway.graphite.fake import FakeGraphite

        repo_root = Path("/fake/repo")
        # Branch "feature" does not exist in local_branches
        git = FakeGit(local_branches={repo_root: ["main"]})
        graphite = FakeGraphite()
        ctx = context_for_test(git=git, graphite=graphite)

        # Should not raise - branch will be created and tracked
        Ensure.branch_graphite_tracked_or_new(ctx, repo_root, "feature", "main")

    def test_succeeds_when_branch_exists_and_tracked(self) -> None:
        """No-op when branch exists and is already tracked by Graphite."""
        from erk_shared.gateway.git.fake import FakeGit
        from erk_shared.gateway.graphite.fake import FakeGraphite
        from erk_shared.gateway.graphite.types import BranchMetadata

        repo_root = Path("/fake/repo")
        # Branch "feature" exists locally AND is tracked by Graphite
        git = FakeGit(local_branches={repo_root: ["main", "feature"]})
        graphite = FakeGraphite(
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha="abc123",
                )
            }
        )
        ctx = context_for_test(git=git, graphite=graphite)

        # Should not raise - branch is tracked
        Ensure.branch_graphite_tracked_or_new(ctx, repo_root, "feature", "main")

    def test_exits_when_branch_exists_but_not_tracked(self) -> None:
        """UserFacingCliError when branch exists locally but is not tracked by Graphite."""
        from erk_shared.gateway.git.fake import FakeGit
        from erk_shared.gateway.graphite.fake import FakeGraphite

        repo_root = Path("/fake/repo")
        # Branch "feature" exists locally but NOT tracked by Graphite
        git = FakeGit(local_branches={repo_root: ["main", "feature"]})
        graphite = FakeGraphite(branches={})  # Empty - no tracked branches
        ctx = context_for_test(git=git, graphite=graphite)

        with pytest.raises(UserFacingCliError):
            Ensure.branch_graphite_tracked_or_new(ctx, repo_root, "feature", "main")

    def test_error_message_includes_remediation_steps(self) -> None:
        """Error message includes all three remediation options."""
        from erk_shared.gateway.git.fake import FakeGit
        from erk_shared.gateway.graphite.fake import FakeGraphite

        repo_root = Path("/fake/repo")
        git = FakeGit(local_branches={repo_root: ["main", "feature"]})
        graphite = FakeGraphite(branches={})
        ctx = context_for_test(git=git, graphite=graphite)

        with pytest.raises(UserFacingCliError) as exc_info:
            Ensure.branch_graphite_tracked_or_new(ctx, repo_root, "feature", "main")

        assert "Branch 'feature' exists but is not tracked by Graphite" in exc_info.value.message
        # Check all three remediation options
        assert "gt track --parent main" in exc_info.value.message
        assert "git branch -D feature" in exc_info.value.message
        assert "erk config set use_graphite false" in exc_info.value.message
