"""Tests for erk pr submit command.

These tests verify the CLI integration with the execute_submit_pr operation.
The operation itself is tested separately in packages/dot-agent-kit/tests.
"""

from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from erk_shared.git.abc import Git
from erk_shared.git.fake import FakeGit
from erk_shared.github.abc import GitHub
from erk_shared.integrations.ai.abc import ClaudeCLIExecutor
from erk_shared.integrations.graphite.abc import Graphite
from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent
from erk_shared.integrations.gt.types import SubmitPRError, SubmitPRResult
from erk_shared.integrations.time.abc import Time

from erk.cli.commands.pr import pr_group
from erk.core.context import ErkContext


@dataclass
class MockGtKit:
    """Simple mock GtKit for testing."""

    git: Git
    github: GitHub
    graphite: Graphite
    ai: ClaudeCLIExecutor
    time: Time


def _create_success_submit_result() -> SubmitPRResult:
    """Create a successful submit result."""
    return SubmitPRResult(
        success=True,
        pr_number=123,
        pr_url="https://github.com/owner/repo/pull/123",
        pr_title="feat: Test feature",
        graphite_url="https://app.graphite.dev/github/pr/owner/repo/123",
        branch_name="feature-branch",
        issue_number=None,
        message="PR #123 submitted successfully",
    )


def _create_auth_error() -> SubmitPRError:
    """Create an authentication error result."""
    return SubmitPRError(
        success=False,
        error_type="preflight_failed",
        message="Graphite CLI (gt) is not authenticated",
        details={"original_error_type": "gt_not_authenticated"},
    )


def _create_no_commits_error() -> SubmitPRError:
    """Create a no commits error result."""
    return SubmitPRError(
        success=False,
        error_type="preflight_failed",
        message="No commits found in branch",
        details={"original_error_type": "no_commits"},
    )


def _mock_execute_submit_pr_success(
    ops, cwd, session_id, *, force=False, publish=True
) -> Generator[ProgressEvent | CompletionEvent[SubmitPRResult | SubmitPRError]]:
    """Mock execute_submit_pr that returns success."""
    yield ProgressEvent("Running preflight checks...")
    yield ProgressEvent("Preflight complete", style="success")
    yield ProgressEvent("Generating commit message via AI...")
    yield ProgressEvent("Commit message generated", style="success")
    yield ProgressEvent("Updating PR metadata...")
    yield ProgressEvent("PR metadata updated", style="success")
    yield CompletionEvent(_create_success_submit_result())


def _mock_execute_submit_pr_auth_error(
    ops, cwd, session_id, *, force=False, publish=True
) -> Generator[ProgressEvent | CompletionEvent[SubmitPRResult | SubmitPRError]]:
    """Mock execute_submit_pr that returns auth error."""
    yield ProgressEvent("Running preflight checks...")
    yield CompletionEvent(_create_auth_error())


def _mock_execute_submit_pr_no_commits(
    ops, cwd, session_id, *, force=False, publish=True
) -> Generator[ProgressEvent | CompletionEvent[SubmitPRResult | SubmitPRError]]:
    """Mock execute_submit_pr that returns no commits error."""
    yield ProgressEvent("Running preflight checks...")
    yield CompletionEvent(_create_no_commits_error())


def test_pr_submit_success(tmp_path: Path) -> None:
    """Test successful PR submission displays PR URL."""
    runner = CliRunner()

    with patch(
        "erk.cli.commands.pr.submit_cmd.execute_submit_pr",
        side_effect=_mock_execute_submit_pr_success,
    ):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            ctx = ErkContext.for_test(
                git=FakeGit(current_branches={tmp_path: "feature-branch"}),
                cwd=tmp_path,
            )

            result = runner.invoke(pr_group, ["submit"], obj=ctx)

    assert result.exit_code == 0
    assert "https://github.com/owner/repo/pull/123" in result.output


def test_pr_submit_displays_graphite_url(tmp_path: Path) -> None:
    """Test that Graphite URL is displayed when available."""
    runner = CliRunner()

    with patch(
        "erk.cli.commands.pr.submit_cmd.execute_submit_pr",
        side_effect=_mock_execute_submit_pr_success,
    ):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            ctx = ErkContext.for_test(
                git=FakeGit(current_branches={tmp_path: "feature-branch"}),
                cwd=tmp_path,
            )

            result = runner.invoke(pr_group, ["submit"], obj=ctx)

    assert result.exit_code == 0
    assert "app.graphite.dev" in result.output


def test_pr_submit_fails_when_not_authenticated(tmp_path: Path) -> None:
    """Test that command fails when Graphite is not authenticated."""
    runner = CliRunner()

    with patch(
        "erk.cli.commands.pr.submit_cmd.execute_submit_pr",
        side_effect=_mock_execute_submit_pr_auth_error,
    ):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            ctx = ErkContext.for_test(
                git=FakeGit(current_branches={tmp_path: "feature-branch"}),
                cwd=tmp_path,
            )

            result = runner.invoke(pr_group, ["submit"], obj=ctx)

    assert result.exit_code != 0
    assert "not authenticated" in result.output.lower()


def test_pr_submit_fails_when_no_commits(tmp_path: Path) -> None:
    """Test that command fails when branch has no commits."""
    runner = CliRunner()

    with patch(
        "erk.cli.commands.pr.submit_cmd.execute_submit_pr",
        side_effect=_mock_execute_submit_pr_no_commits,
    ):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            ctx = ErkContext.for_test(
                git=FakeGit(current_branches={tmp_path: "feature-branch"}),
                cwd=tmp_path,
            )

            result = runner.invoke(pr_group, ["submit"], obj=ctx)

    assert result.exit_code != 0
    assert "no commits" in result.output.lower()


def test_pr_submit_with_force_flag(tmp_path: Path) -> None:
    """Test that --force flag is passed through."""
    runner = CliRunner()
    captured_force = []

    def mock_with_force_capture(ops, cwd, session_id, *, force=False, publish=True):
        captured_force.append(force)
        yield from _mock_execute_submit_pr_success(
            ops, cwd, session_id, force=force, publish=publish
        )

    with patch(
        "erk.cli.commands.pr.submit_cmd.execute_submit_pr",
        side_effect=mock_with_force_capture,
    ):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            ctx = ErkContext.for_test(
                git=FakeGit(current_branches={tmp_path: "feature-branch"}),
                cwd=tmp_path,
            )

            result = runner.invoke(pr_group, ["submit", "--force"], obj=ctx)

    assert result.exit_code == 0
    assert captured_force == [True]
