"""Tests for erk exec get-pr-context command."""

import json

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_pr_context import get_pr_context
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.plan_store.github import GitHubPlanStore
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _make_pr_details(
    *,
    number: int,
    branch: str,
    body: str = "",
) -> PRDetails:
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title="WIP",
        body=body,
        base_ref_name="main",
        head_ref_name=branch,
        state="OPEN",
        is_draft=False,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


def test_outputs_valid_json() -> None:
    """Happy path: outputs valid JSON with all expected fields."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
            diff_to_branch={(env.cwd, "main"): "diff --git a/file.py b/file.py\n+new content"},
            commit_messages_since={(env.cwd, "main"): ["Initial commit"]},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature"],
                    is_trunk=True,
                    commit_sha=None,
                ),
            },
        )

        pr_details = _make_pr_details(number=42, branch="feature")
        github = FakeGitHub(
            authenticated=True,
            prs_by_branch={"feature": pr_details},
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            github=github,
            plan_store=GitHubPlanStore(FakeGitHubIssues()),
        )

        result = runner.invoke(get_pr_context, [], obj=ctx)

        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["branch"]["current"] == "feature"
        assert data["branch"]["parent"] == "main"
        assert data["pr"]["number"] == 42
        assert data["pr"]["url"] == "https://github.com/owner/repo/pull/42"
        assert "diff_file" in data
        assert data["commit_messages"] == ["Initial commit"]
        assert data["plan_context"] is None


def test_fails_when_no_pr() -> None:
    """Exits 1 with clear error when no PR exists for the branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
        )

        graphite = FakeGraphite(
            authenticated=True,
            branches={
                "feature": BranchMetadata(
                    name="feature",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature"],
                    is_trunk=True,
                    commit_sha=None,
                ),
            },
        )

        github = FakeGitHub(authenticated=True)

        ctx = build_workspace_test_context(env, git=git, graphite=graphite, github=github)

        result = runner.invoke(get_pr_context, [], obj=ctx)

        assert result.exit_code != 0
        assert "No pull request found" in result.output


def test_fails_when_not_on_branch() -> None:
    """Exits 1 when in detached HEAD state."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: None},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(get_pr_context, [], obj=ctx)

        assert result.exit_code != 0
        assert "Not on a branch" in result.output
