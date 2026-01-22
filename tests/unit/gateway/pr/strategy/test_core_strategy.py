"""Tests for CoreSubmitStrategy.

Tests verify the strategy pattern wrapper around execute_core_submit,
ensuring it correctly converts CoreSubmitResult/CoreSubmitError to
the unified SubmitStrategyResult/SubmitStrategyError types.
"""

from pathlib import Path

from erk_shared.context.context import ErkContext
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.strategy.core import CoreSubmitStrategy
from erk_shared.gateway.pr.strategy.types import (
    SubmitStrategyError,
    SubmitStrategyResult,
)
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo


def _collect_result(
    strategy: CoreSubmitStrategy,
    ctx: ErkContext,
    cwd: Path,
    *,
    force: bool,
) -> SubmitStrategyResult | SubmitStrategyError:
    """Execute strategy and collect the final result."""
    result: SubmitStrategyResult | SubmitStrategyError | None = None

    for event in strategy.execute(ctx, cwd, force=force):
        if isinstance(event, CompletionEvent):
            result = event.result

    if result is None:
        raise AssertionError("Strategy did not yield a CompletionEvent")

    return result


def test_core_strategy_creates_pr_successfully(tmp_path: Path) -> None:
    """CoreSubmitStrategy creates PR and returns SubmitStrategyResult."""
    cwd = tmp_path

    # Configure FakeGit
    git = FakeGit(
        repository_roots={cwd: cwd},
        git_common_dirs={cwd: cwd},
        local_branches={cwd: ["main", "feature"]},
        current_branches={cwd: "feature"},
        trunk_branches={cwd: "main"},
        commits_ahead={(cwd, "main"): 1},
        remote_urls={(cwd, "origin"): "git@github.com:owner/repo.git"},
    )

    # No existing PR - will be created
    pr_details = PRDetails(
        number=999,
        url="https://github.com/owner/repo/pull/999",
        title="WIP",
        body="",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
        labels=(),
    )

    github = FakeGitHub(
        authenticated=True,
        prs={},  # No existing PR
        pr_details={999: pr_details},
        pr_bases={999: "main"},
    )

    ctx = ErkContext.for_test(
        git=git,
        github=github,
        cwd=cwd,
        repo_root=cwd,
    )

    strategy = CoreSubmitStrategy(
        pr_title="WIP",
        pr_body="",
        plans_repo=None,
    )

    result = _collect_result(strategy, ctx, cwd, force=False)

    # Verify result type
    assert isinstance(result, SubmitStrategyResult)
    assert result.pr_number == 999
    assert result.graphite_url is None  # CoreStrategy has no Graphite URL
    assert result.was_created is True
    assert result.branch_name == "feature"
    assert result.base_branch == "main"


def test_core_strategy_updates_existing_pr(tmp_path: Path) -> None:
    """CoreSubmitStrategy updates existing PR instead of creating new one."""
    cwd = tmp_path

    # Configure existing PR
    pr_info = PullRequestInfo(
        number=123,
        state="OPEN",
        url="https://github.com/owner/repo/pull/123",
        is_draft=False,
        title="Old title",
        checks_passing=True,
        owner="owner",
        repo="repo",
    )
    pr_details = PRDetails(
        number=123,
        url="https://github.com/owner/repo/pull/123",
        title="Old title",
        body="",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
        labels=(),
    )

    git = FakeGit(
        repository_roots={cwd: cwd},
        git_common_dirs={cwd: cwd},
        local_branches={cwd: ["main", "feature"]},
        current_branches={cwd: "feature"},
        trunk_branches={cwd: "main"},
        commits_ahead={(cwd, "main"): 1},
        remote_urls={(cwd, "origin"): "git@github.com:owner/repo.git"},
    )

    github = FakeGitHub(
        authenticated=True,
        prs={"feature": pr_info},  # Existing PR
        pr_details={123: pr_details},
        pr_bases={123: "main"},
    )

    ctx = ErkContext.for_test(
        git=git,
        github=github,
        cwd=cwd,
        repo_root=cwd,
    )

    strategy = CoreSubmitStrategy(
        pr_title="Updated title",
        pr_body="Updated body",
        plans_repo=None,
    )

    result = _collect_result(strategy, ctx, cwd, force=False)

    # Verify PR was updated, not created
    assert isinstance(result, SubmitStrategyResult)
    assert result.pr_number == 123
    assert result.was_created is False


def test_core_strategy_handles_auth_failure(tmp_path: Path) -> None:
    """CoreSubmitStrategy returns error when GitHub auth fails."""
    cwd = tmp_path

    git = FakeGit(
        repository_roots={cwd: cwd},
        git_common_dirs={cwd: cwd},
        local_branches={cwd: ["main", "feature"]},
        current_branches={cwd: "feature"},
    )

    # Simulate auth failure
    github = FakeGitHub(authenticated=False)

    ctx = ErkContext.for_test(
        git=git,
        github=github,
        cwd=cwd,
        repo_root=cwd,
    )

    strategy = CoreSubmitStrategy(
        pr_title="Title",
        pr_body="Body",
        plans_repo=None,
    )

    result = _collect_result(strategy, ctx, cwd, force=False)

    # Verify error
    assert isinstance(result, SubmitStrategyError)
    assert result.error_type == "github_auth_failed"


def test_core_strategy_handles_no_commits(tmp_path: Path) -> None:
    """CoreSubmitStrategy returns error when branch has no commits ahead."""
    cwd = tmp_path

    git = FakeGit(
        repository_roots={cwd: cwd},
        git_common_dirs={cwd: cwd},
        local_branches={cwd: ["main", "feature"]},
        current_branches={cwd: "feature"},
        trunk_branches={cwd: "main"},
        commits_ahead={(cwd, "main"): 0},  # No commits ahead
        remote_urls={(cwd, "origin"): "git@github.com:owner/repo.git"},
    )

    github = FakeGitHub(authenticated=True)

    ctx = ErkContext.for_test(
        git=git,
        github=github,
        cwd=cwd,
        repo_root=cwd,
    )

    strategy = CoreSubmitStrategy(
        pr_title="Title",
        pr_body="Body",
        plans_repo=None,
    )

    result = _collect_result(strategy, ctx, cwd, force=False)

    # Verify error
    assert isinstance(result, SubmitStrategyError)
    assert result.error_type == "no_commits"


def test_core_strategy_handles_detached_head(tmp_path: Path) -> None:
    """CoreSubmitStrategy returns error when in detached HEAD state."""
    cwd = tmp_path

    git = FakeGit(
        repository_roots={cwd: cwd},
        git_common_dirs={cwd: cwd},
        local_branches={cwd: ["main"]},
        current_branches={cwd: None},  # Detached HEAD
    )

    github = FakeGitHub(authenticated=True)

    ctx = ErkContext.for_test(
        git=git,
        github=github,
        cwd=cwd,
        repo_root=cwd,
    )

    strategy = CoreSubmitStrategy(
        pr_title="Title",
        pr_body="Body",
        plans_repo=None,
    )

    result = _collect_result(strategy, ctx, cwd, force=False)

    # Verify error
    assert isinstance(result, SubmitStrategyError)
    assert result.error_type == "no_branch"


def test_core_strategy_yields_progress_events(tmp_path: Path) -> None:
    """CoreSubmitStrategy yields progress events during execution."""
    cwd = tmp_path

    pr_details = PRDetails(
        number=999,
        url="https://github.com/owner/repo/pull/999",
        title="WIP",
        body="",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
        labels=(),
    )

    git = FakeGit(
        repository_roots={cwd: cwd},
        git_common_dirs={cwd: cwd},
        local_branches={cwd: ["main", "feature"]},
        current_branches={cwd: "feature"},
        trunk_branches={cwd: "main"},
        commits_ahead={(cwd, "main"): 1},
        remote_urls={(cwd, "origin"): "git@github.com:owner/repo.git"},
    )

    github = FakeGitHub(
        authenticated=True,
        prs={},
        pr_details={999: pr_details},
        pr_bases={999: "main"},
    )

    ctx = ErkContext.for_test(
        git=git,
        github=github,
        cwd=cwd,
        repo_root=cwd,
    )

    strategy = CoreSubmitStrategy(
        pr_title="WIP",
        pr_body="",
        plans_repo=None,
    )

    # Collect all events
    progress_events: list[ProgressEvent] = []
    completion_event: CompletionEvent | None = None

    for event in strategy.execute(ctx, cwd, force=False):
        if isinstance(event, ProgressEvent):
            progress_events.append(event)
        elif isinstance(event, CompletionEvent):
            completion_event = event

    # Should have multiple progress events
    assert len(progress_events) > 0
    # Should have exactly one completion event
    assert completion_event is not None
    # Progress events should have messages
    for pe in progress_events:
        assert pe.message is not None
