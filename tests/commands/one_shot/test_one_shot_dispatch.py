"""Tests for one-shot dispatch shared logic via RemoteGitHub."""

from erk.cli.commands.one_shot_remote_dispatch import (
    OneShotDispatchParams,
    OneShotDryRunResult,
    dispatch_one_shot_remote,
)
from tests.fakes.gateway.remote_github import FakeRemoteGitHub
from tests.fakes.gateway.time import FakeTime


def test_dispatch_happy_path() -> None:
    """Test dispatch creates plnd/ branch, PR with metadata, and triggers workflow."""
    remote = FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    time = FakeTime()

    params = OneShotDispatchParams(
        prompt="fix the import in config.py",
        model=None,
        extra_workflow_inputs={},
        slug=None,
    )

    result = dispatch_one_shot_remote(
        remote=remote,
        owner="owner",
        repo="repo",
        params=params,
        dry_run=False,
        ref=None,
        time_gateway=time,
        prompt_executor=None,
    )

    assert result is not None
    # Branch should have plnd/ prefix (planned-PR naming)
    assert result.branch_name.startswith("plnd/")
    assert result.pr_url == "https://github.com/owner/repo/pull/1"
    assert result.run_url == "https://github.com/owner/repo/actions/runs/run-1"

    # Verify branch was created
    assert len(remote.created_refs) == 1
    assert remote.created_refs[0].ref.startswith("refs/heads/plnd/")
    assert remote.created_refs[0].sha == "abc123"

    # Verify .erk/impl-context/prompt.md was committed
    assert len(remote.created_file_commits) == 1
    commit = remote.created_file_commits[0]
    assert commit.path == ".erk/impl-context/prompt.md"
    assert commit.content == "fix the import in config.py\n"
    assert commit.branch.startswith("plnd/")

    # Verify PR was created as draft with plan-header metadata
    assert len(remote.created_pull_requests) == 1
    pr = remote.created_pull_requests[0]
    assert pr.draft is True
    assert pr.base == "main"
    assert "plan-header" in pr.body

    # Verify erk-plan label added to PR
    assert len(remote.added_labels) == 1
    assert remote.added_labels[0].labels == ("erk-pr", "erk-plan", "erk-core")

    # Verify workflow was triggered with plan_backend=planned_pr
    assert len(remote.dispatched_workflows) == 1
    wf = remote.dispatched_workflows[0]
    assert wf.workflow == "one-shot.yml"
    assert wf.inputs["prompt"] == "fix the import in config.py"
    assert wf.inputs["plan_backend"] == "planned_pr"
    assert wf.inputs["plan_issue_number"] == "1"


def test_dispatch_with_extra_inputs() -> None:
    """Test extra_workflow_inputs are passed in workflow trigger."""
    remote = FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    time = FakeTime()

    params = OneShotDispatchParams(
        prompt="implement step 1.1",
        model=None,
        extra_workflow_inputs={
            "objective_issue": "42",
            "node_id": "1.1",
        },
        slug=None,
    )

    result = dispatch_one_shot_remote(
        remote=remote,
        owner="owner",
        repo="repo",
        params=params,
        dry_run=False,
        ref=None,
        time_gateway=time,
        prompt_executor=None,
    )

    assert result is not None
    assert result.branch_name.startswith("plnd/")
    assert "owner/repo/pull/1" in result.pr_url
    assert "owner/repo/actions/runs/run-1" in result.run_url

    # Verify extra inputs are in workflow trigger
    wf = remote.dispatched_workflows[0]
    assert wf.inputs["objective_issue"] == "42"
    assert wf.inputs["node_id"] == "1.1"
    assert wf.inputs["prompt"] == "implement step 1.1"


def test_dispatch_dry_run() -> None:
    """Test dispatch dry_run outputs info without mutations."""
    remote = FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    time = FakeTime()

    params = OneShotDispatchParams(
        prompt="add type hints",
        model="opus",
        extra_workflow_inputs={},
        slug=None,
    )

    result = dispatch_one_shot_remote(
        remote=remote,
        owner="owner",
        repo="repo",
        params=params,
        dry_run=True,
        ref=None,
        time_gateway=time,
        prompt_executor=None,
    )

    assert isinstance(result, OneShotDryRunResult)

    # Verify no mutations occurred
    assert len(remote.created_refs) == 0
    assert len(remote.created_file_commits) == 0
    assert len(remote.created_pull_requests) == 0
    assert len(remote.dispatched_workflows) == 0


def test_dispatch_with_pre_generated_slug_skips_llm() -> None:
    """Test that providing a slug skips LLM slug generation and uses slug directly."""
    remote = FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    time = FakeTime()

    params = OneShotDispatchParams(
        prompt="fix the import in config.py",
        model=None,
        extra_workflow_inputs={},
        slug="fix-config-import",
    )

    result = dispatch_one_shot_remote(
        remote=remote,
        owner="owner",
        repo="repo",
        params=params,
        dry_run=False,
        ref=None,
        time_gateway=time,
        prompt_executor=None,
    )

    assert result is not None
    # Branch should contain the pre-generated slug
    assert "fix-config-import" in result.branch_name
    assert result.branch_name.startswith("plnd/")
    assert result.pr_url is not None
    assert result.run_url is not None


def test_dispatch_long_prompt_truncates_workflow_input() -> None:
    """Test that long prompts are truncated in workflow input but committed in full."""
    remote = FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    time = FakeTime()

    long_prompt = "x" * 1000

    params = OneShotDispatchParams(
        prompt=long_prompt,
        model=None,
        extra_workflow_inputs={},
        slug=None,
    )

    result = dispatch_one_shot_remote(
        remote=remote,
        owner="owner",
        repo="repo",
        params=params,
        dry_run=False,
        ref=None,
        time_gateway=time,
        prompt_executor=None,
    )

    assert result is not None
    assert result.pr_url is not None
    assert result.run_url is not None

    # Verify workflow input was truncated
    wf = remote.dispatched_workflows[0]
    assert len(wf.inputs["prompt"]) < len(long_prompt)
    assert wf.inputs["prompt"].endswith(
        "... (full prompt committed to .erk/impl-context/prompt.md)"
    )

    # Verify full prompt was committed
    assert len(remote.created_file_commits) == 1
    assert remote.created_file_commits[0].content == long_prompt + "\n"


def test_dispatch_explicit_ref_is_passed_to_workflow() -> None:
    """Test that an explicit ref is threaded through to dispatch_workflow."""
    remote = FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    time = FakeTime()

    params = OneShotDispatchParams(
        prompt="fix the import in config.py",
        model=None,
        extra_workflow_inputs={},
        slug=None,
    )

    result = dispatch_one_shot_remote(
        remote=remote,
        owner="owner",
        repo="repo",
        params=params,
        dry_run=False,
        ref="custom-ref",
        time_gateway=time,
        prompt_executor=None,
    )

    assert result is not None
    assert result.pr_url is not None
    assert result.run_url is not None
    assert len(remote.dispatched_workflows) == 1
    assert remote.dispatched_workflows[0].ref == "custom-ref"
