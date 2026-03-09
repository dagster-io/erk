"""Tests for consolidate-learn-plans dispatch logic via RemoteGitHub."""

from erk.cli.commands.consolidate_learn_plans_dispatch import (
    dispatch_consolidate_learn_plans,
)
from erk_shared.fakes.remote_github import FakeRemoteGitHub
from erk_shared.fakes.time import FakeTime


def _make_remote(
    *,
    next_pr_number: int = 1,
    dispatch_run_id: str = "run-1",
) -> FakeRemoteGitHub:
    return FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=next_pr_number,
        dispatch_run_id=dispatch_run_id,
        issues=None,
        issue_comments=None,
        pr_references=None,
    )


def test_dispatch_happy_path() -> None:
    """Test dispatch creates branch, draft PR with labels, and triggers workflow."""
    remote = _make_remote()
    time = FakeTime()

    result = dispatch_consolidate_learn_plans(
        remote=remote,
        owner="owner",
        repo="repo",
        model=None,
        dry_run=False,
        ref=None,
        time_gateway=time,
    )

    assert result is not None
    assert result.pr_number == 1
    assert result.run_id == "run-1"

    # Branch name format: consolidate-learn-plans-{MM-DD-HHMM}
    assert result.branch_name.startswith("consolidate-learn-plans-")

    # Verify branch was created from trunk SHA
    assert len(remote.created_refs) == 1
    assert remote.created_refs[0].ref == f"refs/heads/{result.branch_name}"
    assert remote.created_refs[0].sha == "abc123"

    # Verify prompt file was committed
    assert len(remote.created_file_commits) == 1
    commit = remote.created_file_commits[0]
    assert commit.path == ".erk/impl-context/prompt.md"
    assert "consolidate" in commit.content.lower()
    assert commit.branch == result.branch_name

    # Verify PR was created as draft with plan-header metadata
    assert len(remote.created_pull_requests) == 1
    pr = remote.created_pull_requests[0]
    assert pr.draft is True
    assert pr.base == "main"
    assert pr.title == "Consolidate learn plans"
    assert "plan-header" in pr.body

    # Verify erk-pr, erk-plan, and erk-learn labels added
    assert len(remote.added_labels) == 1
    assert remote.added_labels[0].labels == ("erk-pr", "erk-plan", "erk-learn")

    # Verify workflow was triggered
    assert len(remote.dispatched_workflows) == 1
    wf = remote.dispatched_workflows[0]
    assert wf.workflow == "consolidate-learn-plans.yml"
    assert wf.inputs["branch_name"] == result.branch_name
    assert wf.inputs["pr_number"] == "1"
    assert wf.inputs["submitted_by"] == "testuser"
    # Default ref is trunk when ref=None
    assert wf.ref == "main"


def test_dispatch_with_model() -> None:
    """Test model is passed through to workflow inputs."""
    remote = _make_remote()
    time = FakeTime()

    result = dispatch_consolidate_learn_plans(
        remote=remote,
        owner="owner",
        repo="repo",
        model="claude-sonnet-4-6",
        dry_run=False,
        ref=None,
        time_gateway=time,
    )

    assert result is not None
    wf = remote.dispatched_workflows[0]
    assert wf.inputs["model_name"] == "claude-sonnet-4-6"


def test_dispatch_dry_run() -> None:
    """Test dry_run outputs info without mutations."""
    remote = _make_remote()
    time = FakeTime()

    result = dispatch_consolidate_learn_plans(
        remote=remote,
        owner="owner",
        repo="repo",
        model=None,
        dry_run=True,
        ref=None,
        time_gateway=time,
    )

    assert result is None

    # Verify no mutations occurred
    assert len(remote.created_refs) == 0
    assert len(remote.created_file_commits) == 0
    assert len(remote.created_pull_requests) == 0
    assert len(remote.dispatched_workflows) == 0


def test_dispatch_explicit_ref() -> None:
    """Test explicit ref is threaded through to dispatch_workflow."""
    remote = _make_remote()
    time = FakeTime()

    result = dispatch_consolidate_learn_plans(
        remote=remote,
        owner="owner",
        repo="repo",
        model=None,
        dry_run=False,
        ref="custom-ref",
        time_gateway=time,
    )

    assert result is not None
    assert len(remote.dispatched_workflows) == 1
    assert remote.dispatched_workflows[0].ref == "custom-ref"


def test_branch_naming_format() -> None:
    """Test branch name follows consolidate-learn-plans-{MM-DD-HHMM} format."""
    remote = _make_remote()
    time = FakeTime()

    result = dispatch_consolidate_learn_plans(
        remote=remote,
        owner="owner",
        repo="repo",
        model=None,
        dry_run=False,
        ref=None,
        time_gateway=time,
    )

    assert result is not None
    # FakeTime returns a fixed datetime; just verify the prefix is correct
    assert result.branch_name.startswith("consolidate-learn-plans-")
    # The timestamp suffix should be -MM-DD-HHMM format (11 chars)
    suffix = result.branch_name[len("consolidate-learn-plans") :]
    # Should match -MM-DD-HHMM pattern (e.g., -01-15-1430)
    assert len(suffix) == 11
    assert suffix[0] == "-"


def test_no_model_input_when_none() -> None:
    """Test model_name key is absent from workflow inputs when model is None."""
    remote = _make_remote()
    time = FakeTime()

    dispatch_consolidate_learn_plans(
        remote=remote,
        owner="owner",
        repo="repo",
        model=None,
        dry_run=False,
        ref=None,
        time_gateway=time,
    )

    wf = remote.dispatched_workflows[0]
    assert "model_name" not in wf.inputs
