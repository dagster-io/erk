"""Tests for one-shot dispatch from outside a git repository."""

from unittest.mock import patch

import click
from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands.one_shot_dispatch import (
    OneShotDispatchParams,
    dispatch_one_shot,
)
from erk.core.context import context_for_test
from erk_shared.context.types import NoRepoSentinel
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_outside_repo_requires_repo_flag() -> None:
    """Verify error when outside repo without --repo flag."""
    issues = FakeGitHubIssues()
    github = FakeGitHub(authenticated=True, issues_gateway=issues)

    ctx = context_for_test(
        github=github,
        issues=issues,
        repo=NoRepoSentinel(),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["one-shot", "fix the import in config.py"],
        obj=ctx,
    )

    assert result.exit_code != 0
    assert "Not in a git repository" in result.output


def test_outside_repo_with_repo_flag_dispatches_via_api() -> None:
    """Verify API-only dispatch path is used when --repo is provided outside a repo."""
    issues = FakeGitHubIssues()
    github = FakeGitHub(authenticated=True, issues_gateway=issues)

    ctx = context_for_test(
        github=github,
        issues=issues,
        repo=NoRepoSentinel(),
    )

    params = OneShotDispatchParams(
        prompt="fix the import in config.py",
        model=None,
        extra_workflow_inputs={},
        slug="fix-import",
        target_repo="owner/repo",
    )

    # Mock the API-only functions since they make real subprocess calls
    with (
        patch("erk.cli.commands.one_shot_dispatch.api_get_default_branch") as mock_default,
        patch("erk.cli.commands.one_shot_dispatch.api_get_branch_sha") as mock_sha,
        patch("erk.cli.commands.one_shot_dispatch.api_create_branch") as mock_create,
        patch("erk.cli.commands.one_shot_dispatch.api_commit_file") as mock_commit,
    ):
        mock_default.return_value = "main"
        mock_sha.return_value = "abc123def456"

        result = dispatch_one_shot(ctx, params=params, dry_run=False, ref=None)

    assert result is not None
    assert result.branch_name.startswith("plnd/")

    # Verify API functions were called instead of local git
    mock_default.assert_called_once_with("owner/repo")
    mock_sha.assert_called_once_with("owner/repo", "main")
    mock_create.assert_called_once()
    mock_commit.assert_called_once()

    # Verify no local git operations
    assert len(github.created_prs) == 1
    assert len(github.triggered_workflows) == 1

    # Verify workflow inputs
    _workflow, inputs, _ref = github.triggered_workflows[0]
    assert inputs["prompt"] == "fix the import in config.py"
    assert inputs["plan_backend"] == "planned_pr"


def test_outside_repo_dry_run_with_repo_flag() -> None:
    """Verify dry-run mode works with --repo flag outside a repo."""
    issues = FakeGitHubIssues()
    github = FakeGitHub(authenticated=True, issues_gateway=issues)

    ctx = context_for_test(
        github=github,
        issues=issues,
        repo=NoRepoSentinel(),
    )

    params = OneShotDispatchParams(
        prompt="fix the import",
        model=None,
        extra_workflow_inputs={},
        slug="fix-import",
        target_repo="owner/repo",
    )

    with patch("erk.cli.commands.one_shot_dispatch.api_get_default_branch") as mock_default:
        mock_default.return_value = "main"
        result = dispatch_one_shot(ctx, params=params, dry_run=True, ref=None)

    # Dry run returns None
    assert result is None
    # No mutations
    assert len(github.created_prs) == 0
    assert len(github.triggered_workflows) == 0


def test_inside_repo_with_repo_override() -> None:
    """Verify --repo overrides local repo when inside a git repo."""
    runner = CliRunner()

    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        issues = FakeGitHubIssues()
        github = FakeGitHub(authenticated=True, issues_gateway=issues)

        ctx = build_workspace_test_context(env, git=git, github=github, issues=issues)

        params = OneShotDispatchParams(
            prompt="fix the import",
            model=None,
            extra_workflow_inputs={},
            slug="fix-import",
            target_repo="other-owner/other-repo",
        )

        # When target_repo is provided but we're inside a repo,
        # local git operations are used (use_api_only is False)
        result = dispatch_one_shot(ctx, params=params, dry_run=False, ref=None)

        assert result is not None
        # Local git path should be used (not API-only)
        assert len(git.created_branches) == 1
        assert len(git.pushed_branches) == 1


def test_ref_current_disallowed_outside_repo() -> None:
    """Verify --ref-current error when outside a repo."""
    from erk.cli.commands.ref_resolution import resolve_dispatch_ref

    ctx = context_for_test(repo=NoRepoSentinel())

    raised = False
    try:
        resolve_dispatch_ref(ctx, dispatch_ref=None, ref_current=True)
    except click.UsageError as e:
        raised = True
        assert "requires being in a git repository" in str(e)

    assert raised, "Expected click.UsageError for --ref-current outside repo"


def test_invalid_repo_format_rejected() -> None:
    """Verify --repo with invalid format is rejected."""
    issues = FakeGitHubIssues()
    github = FakeGitHub(authenticated=True, issues_gateway=issues)

    ctx = context_for_test(
        github=github,
        issues=issues,
        repo=NoRepoSentinel(),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["one-shot", "fix the import", "--repo", "not-a-valid-repo"],
        obj=ctx,
    )

    assert result.exit_code != 0
    assert "owner/repo" in result.output
