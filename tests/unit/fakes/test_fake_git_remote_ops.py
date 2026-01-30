"""Tests for FakeGitRemoteOps."""

from pathlib import Path

from erk_shared.gateway.git.fake import PushedBranch
from erk_shared.gateway.git.remote_ops.fake import FakeGitRemoteOps
from erk_shared.gateway.git.remote_ops.types import (
    PullRebaseError,
    PullRebaseResult,
    PushError,
    PushResult,
)


class TestPushToRemote:
    def test_returns_push_result_on_success(self) -> None:
        ops = FakeGitRemoteOps()
        result = ops.push_to_remote(
            Path("/repo"), "origin", "main", set_upstream=False, force=False
        )
        assert isinstance(result, PushResult)

    def test_returns_push_error_when_configured(self) -> None:
        error = PushError(message="rejected")
        ops = FakeGitRemoteOps(push_to_remote_error=error)
        result = ops.push_to_remote(
            Path("/repo"), "origin", "main", set_upstream=False, force=False
        )
        assert isinstance(result, PushError)
        assert result.message == "rejected"

    def test_tracks_pushed_branch_on_success(self) -> None:
        ops = FakeGitRemoteOps()
        ops.push_to_remote(Path("/repo"), "origin", "feature", set_upstream=True, force=False)
        assert ops.pushed_branches == [
            PushedBranch(remote="origin", branch="feature", set_upstream=True, force=False)
        ]

    def test_does_not_track_pushed_branch_on_error(self) -> None:
        ops = FakeGitRemoteOps(push_to_remote_error=PushError(message="rejected"))
        ops.push_to_remote(Path("/repo"), "origin", "main", set_upstream=False, force=False)
        assert ops.pushed_branches == []


class TestPullRebase:
    def test_returns_pull_rebase_result_on_success(self) -> None:
        ops = FakeGitRemoteOps()
        result = ops.pull_rebase(Path("/repo"), "origin", "main")
        assert isinstance(result, PullRebaseResult)

    def test_returns_pull_rebase_error_when_configured(self) -> None:
        error = PullRebaseError(message="conflict")
        ops = FakeGitRemoteOps(pull_rebase_error=error)
        result = ops.pull_rebase(Path("/repo"), "origin", "main")
        assert isinstance(result, PullRebaseError)
        assert result.message == "conflict"

    def test_tracks_pull_rebase_call_on_success(self) -> None:
        cwd = Path("/repo")
        ops = FakeGitRemoteOps()
        ops.pull_rebase(cwd, "origin", "main")
        assert ops.pull_rebase_calls == [(cwd, "origin", "main")]

    def test_tracks_pull_rebase_call_even_on_error(self) -> None:
        cwd = Path("/repo")
        ops = FakeGitRemoteOps(pull_rebase_error=PullRebaseError(message="conflict"))
        ops.pull_rebase(cwd, "origin", "main")
        assert ops.pull_rebase_calls == [(cwd, "origin", "main")]
