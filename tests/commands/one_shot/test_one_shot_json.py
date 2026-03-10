"""Tests for erk json one-shot machine command."""

import json

from click.testing import CliRunner

from erk.cli.cli import cli
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.remote_github import FakeRemoteGitHub
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _make_remote() -> FakeRemoteGitHub:
    """Create a default FakeRemoteGitHub for tests."""
    return FakeRemoteGitHub(
        authenticated_user="testuser",
        default_branch_name="main",
        default_branch_sha="abc123",
        next_pr_number=1,
        dispatch_run_id="run-1",
        issues=None,
        issue_comments=None,
        pr_references=None,
    )


def test_json_one_shot_success() -> None:
    """JSON output on successful dispatch via erk json one-shot."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)
        remote = _make_remote()

        ctx = build_workspace_test_context(env, git=git, github=github, remote_github=remote)

        result = runner.invoke(
            cli,
            ["json", "one-shot"],
            input='{"prompt": "fix the import in config.py"}',
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["dry_run"] is False
        assert data["pr_number"] == 1
        assert "pr_url" in data
        assert "run_id" in data
        assert "run_url" in data
        assert "branch_name" in data


def test_json_one_shot_dry_run() -> None:
    """JSON output in dry-run mode via erk json one-shot."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        github = FakeLocalGitHub(authenticated=True)
        remote = _make_remote()

        ctx = build_workspace_test_context(env, git=git, github=github, remote_github=remote)

        result = runner.invoke(
            cli,
            ["json", "one-shot"],
            input='{"prompt": "add type hints", "dry_run": true}',
            obj=ctx,
            catch_exceptions=False,
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        data = json.loads(result.stdout)
        assert data["success"] is True
        assert data["dry_run"] is True
        assert "branch_name" in data
        assert data["prompt"] == "add type hints"
        assert "target" in data
        assert "pr_title" in data
        assert data["base_branch"] == "main"
        assert "submitted_by" in data
        assert "workflow" in data

        # Verify no mutations occurred
        assert len(remote.created_refs) == 0
        assert len(remote.created_pull_requests) == 0
        assert len(remote.dispatched_workflows) == 0


def test_json_one_shot_error_empty_prompt() -> None:
    """Empty prompt produces JSON error via erk json one-shot."""
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
            ["json", "one-shot"],
            input='{"prompt": "   "}',
            obj=ctx,
        )

        assert result.exit_code == 1
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert data["error_type"] == "invalid_input"
        assert "empty" in data["message"].lower()


def test_json_one_shot_error_invalid_repo() -> None:
    """Invalid repo format produces JSON error via erk json one-shot."""
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
            ["json", "one-shot"],
            input='{"prompt": "fix bug", "target_repo": "invalid-format"}',
            obj=ctx,
        )

        assert result.exit_code == 1
        data = json.loads(result.stdout)
        assert data["success"] is False
        assert "error_type" in data


def test_json_one_shot_schema() -> None:
    """--schema flag outputs valid schema document."""
    runner = CliRunner()
    result = runner.invoke(cli, ["json", "one-shot", "--schema"])

    assert result.exit_code == 0
    doc = json.loads(result.output)
    assert doc["command"] == "one_shot"
    assert "input_schema" in doc
    assert "output_schema" in doc
    assert "error_schema" in doc
    assert "prompt" in doc["input_schema"]["properties"]
