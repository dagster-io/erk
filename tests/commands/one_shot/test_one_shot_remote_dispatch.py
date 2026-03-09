"""Tests for one-shot remote dispatch (--repo flag path)."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands.one_shot_remote_dispatch import (
    OneShotDispatchParams,
    OneShotDryRunResult,
    dispatch_one_shot_remote,
)
from tests.fakes.gateway.remote_github import FakeRemoteGitHub
from tests.fakes.gateway.time import FakeTime


def test_remote_dispatch_happy_path() -> None:
    """Test remote dispatch creates branch, PR, and dispatches workflow."""
    remote = FakeRemoteGitHub(
        authenticated_user="alice",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=42,
        dispatch_run_id="run-99",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    time = FakeTime()

    params = OneShotDispatchParams(
        prompt="fix the bug in config.py",
        model=None,
        extra_workflow_inputs={},
        slug="fix-config-bug",
    )

    result = dispatch_one_shot_remote(
        remote=remote,
        owner="test-owner",
        repo="test-repo",
        params=params,
        dry_run=False,
        ref=None,
        time_gateway=time,
        prompt_executor=None,
    )

    assert result is not None
    assert result.pr_number == 42
    assert result.run_id == "run-99"
    assert result.branch_name.startswith("plnd/")

    # Verify branch was created
    assert len(remote.created_refs) == 1
    ref = remote.created_refs[0]
    assert ref.owner == "test-owner"
    assert ref.repo == "test-repo"
    assert ref.ref.startswith("refs/heads/plnd/")
    assert ref.sha == "abc123"

    # Verify prompt was committed
    assert len(remote.created_file_commits) == 1
    commit = remote.created_file_commits[0]
    assert commit.path == ".erk/impl-context/prompt.md"
    assert commit.content == "fix the bug in config.py\n"
    assert commit.branch.startswith("plnd/")

    # Verify PR was created
    assert len(remote.created_pull_requests) == 1
    pr = remote.created_pull_requests[0]
    assert pr.owner == "test-owner"
    assert pr.repo == "test-repo"
    assert pr.base == "main"
    assert pr.draft is True
    assert "One-shot:" in pr.title

    # Verify labels were added
    assert len(remote.added_labels) == 1
    labels = remote.added_labels[0]
    assert labels.labels == ("erk-pr", "erk-plan", "erk-core")

    # Verify workflow was dispatched
    assert len(remote.dispatched_workflows) == 1
    wf = remote.dispatched_workflows[0]
    assert wf.workflow == "one-shot.yml"
    assert wf.inputs["prompt"] == "fix the bug in config.py"
    assert wf.inputs["pr_number"] == "42"
    assert wf.inputs["submitted_by"] == "alice"
    # Dispatch ref should be the feature branch so workflow file comes from branch
    assert wf.ref == result.branch_name


def test_remote_dispatch_dry_run() -> None:
    """Test remote dispatch dry-run shows preview without executing."""
    remote = FakeRemoteGitHub(
        authenticated_user="test-user",
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
        prompt="fix the bug",
        model=None,
        extra_workflow_inputs={},
        slug="fix-bug",
    )

    result = dispatch_one_shot_remote(
        remote=remote,
        owner="test-owner",
        repo="test-repo",
        params=params,
        dry_run=True,
        ref=None,
        time_gateway=time,
        prompt_executor=None,
    )

    assert isinstance(result, OneShotDryRunResult)
    assert result.prompt == "fix the bug"
    assert result.target == "test-owner/test-repo"
    assert result.base_branch == "main"
    assert result.submitted_by == "test-user"
    assert result.workflow == "one-shot.yml"

    # Verify no mutations occurred
    assert len(remote.created_refs) == 0
    assert len(remote.created_file_commits) == 0
    assert len(remote.created_pull_requests) == 0
    assert len(remote.dispatched_workflows) == 0


def test_remote_dispatch_with_model() -> None:
    """Test model is passed through to workflow inputs."""
    remote = FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=10,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    time = FakeTime()

    params = OneShotDispatchParams(
        prompt="fix bug",
        model="opus",
        extra_workflow_inputs={},
        slug="fix-bug",
    )

    result = dispatch_one_shot_remote(
        remote=remote,
        owner="o",
        repo="r",
        params=params,
        dry_run=False,
        ref=None,
        time_gateway=time,
        prompt_executor=None,
    )

    assert result is not None
    wf = remote.dispatched_workflows[0]
    assert wf.inputs["model_name"] == "opus"


def test_remote_dispatch_with_explicit_ref() -> None:
    """Test explicit ref is used for workflow dispatch instead of trunk."""
    remote = FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=10,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    time = FakeTime()

    params = OneShotDispatchParams(
        prompt="fix bug",
        model=None,
        extra_workflow_inputs={},
        slug="fix-bug",
    )

    result = dispatch_one_shot_remote(
        remote=remote,
        owner="o",
        repo="r",
        params=params,
        dry_run=False,
        ref="custom-branch",
        time_gateway=time,
        prompt_executor=None,
    )

    assert result is not None
    wf = remote.dispatched_workflows[0]
    assert wf.ref == "custom-branch"


def test_remote_dispatch_with_plan_only() -> None:
    """Test plan_only extra input is passed through."""
    remote = FakeRemoteGitHub(
        authenticated_user="test-user",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=10,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )
    time = FakeTime()

    params = OneShotDispatchParams(
        prompt="refactor everything",
        model=None,
        extra_workflow_inputs={"plan_only": "true"},
        slug="refactor",
    )

    result = dispatch_one_shot_remote(
        remote=remote,
        owner="o",
        repo="r",
        params=params,
        dry_run=False,
        ref=None,
        time_gateway=time,
        prompt_executor=None,
    )

    assert result is not None
    wf = remote.dispatched_workflows[0]
    assert wf.inputs["plan_only"] == "true"


def test_cli_repo_flag_rejects_invalid_format() -> None:
    """Test --repo flag rejects invalid owner/repo format."""
    from tests.fakes.gateway.git import FakeGit
    from tests.fakes.gateway.github import FakeLocalGitHub
    from tests.test_utils.context_builders import build_workspace_test_context
    from tests.test_utils.env_helpers import erk_isolated_fs_env

    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)
        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            cli,
            ["one-shot", "fix bug", "--repo", "invalid-format"],
            obj=ctx,
        )

        assert result.exit_code == 1
        assert "Invalid --repo format" in result.output


def test_cli_repo_flag_rejects_ref_current() -> None:
    """Test --repo + --ref-current is rejected."""
    from tests.fakes.gateway.git import FakeGit
    from tests.fakes.gateway.github import FakeLocalGitHub
    from tests.test_utils.context_builders import build_workspace_test_context
    from tests.test_utils.env_helpers import erk_isolated_fs_env

    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)
        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(
            cli,
            ["one-shot", "fix bug", "--repo", "owner/repo", "--ref-current"],
            obj=ctx,
        )

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output
