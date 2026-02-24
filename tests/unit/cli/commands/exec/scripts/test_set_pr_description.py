"""Tests for erk exec set-pr-description command."""

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.set_pr_description import set_pr_description
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from erk_shared.plan_store.planned_pr_lifecycle import build_plan_stage_body
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


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


def _make_standard_fakes(
    env,
    *,
    branch_name: str = "feature",
    parent_branch: str = "main",
    pr_body: str = "",
    pr_number: int = 42,
):
    git = FakeGit(
        git_common_dirs={env.cwd: env.git_dir},
        repository_roots={env.cwd: env.git_dir},
        local_branches={env.cwd: ["main", branch_name]},
        default_branches={env.cwd: "main"},
        trunk_branches={env.git_dir: "main"},
        current_branches={env.cwd: branch_name},
    )

    graphite = FakeGraphite(
        authenticated=True,
        branches={
            branch_name: BranchMetadata(
                name=branch_name,
                parent=parent_branch,
                children=[],
                is_trunk=False,
                commit_sha=None,
            ),
            "main": BranchMetadata(
                name="main",
                parent=None,
                children=[branch_name],
                is_trunk=True,
                commit_sha=None,
            ),
        },
    )

    pr_details = _make_pr_details(
        number=pr_number,
        branch=branch_name,
        body=pr_body,
    )
    github = FakeGitHub(
        authenticated=True,
        prs_by_branch={branch_name: pr_details},
    )

    return git, graphite, github


def test_updates_pr_title_and_body() -> None:
    """Happy path: PR title and body are updated."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git, graphite, github = _make_standard_fakes(env)

        ctx = build_workspace_test_context(env, git=git, graphite=graphite, github=github)

        result = runner.invoke(
            set_pr_description,
            ["--title", "Fix auth bug", "--body", "Fixes the authentication issue."],
            obj=ctx,
        )

        assert result.exit_code == 0, result.output
        assert "PR #42 updated" in result.output
        assert "Fix auth bug" in result.output

        # Verify PR was updated on GitHub
        assert len(github.updated_pr_titles) == 1
        assert github.updated_pr_titles[0] == (42, "Fix auth bug")

        assert len(github.updated_pr_bodies) == 1
        pr_number, body = github.updated_pr_bodies[0]
        assert pr_number == 42
        assert "Fixes the authentication issue." in body


def test_generates_footer_with_checkout_command() -> None:
    """Updated body includes footer with checkout command."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git, graphite, github = _make_standard_fakes(env, pr_body="Old content")

        ctx = build_workspace_test_context(env, git=git, graphite=graphite, github=github)

        result = runner.invoke(
            set_pr_description,
            ["--title", "New title", "--body", "New body"],
            obj=ctx,
        )

        assert result.exit_code == 0

        _, updated_body = github.updated_pr_bodies[0]
        assert "New body" in updated_body
        assert "erk pr checkout" in updated_body
        # No issue closing reference (planned-PR only)
        assert "Closes #" not in updated_body


def test_fails_when_no_pr() -> None:
    """Exits 1 when no PR exists for the branch."""
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

        result = runner.invoke(
            set_pr_description,
            ["--title", "Test", "--body", "Test body"],
            obj=ctx,
        )

        assert result.exit_code != 0
        assert "No pull request found" in result.output


def test_planned_pr_backend_preserves_metadata() -> None:
    """Metadata prefix is preserved for draft PR backend."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        metadata_body = format_plan_header_body_for_test()
        plan_content = "# My Plan\n\nImplement the thing."
        pr_body = build_plan_stage_body(metadata_body, plan_content)

        git, graphite, github = _make_standard_fakes(
            env,
            branch_name="feature",
            pr_body=pr_body,
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            graphite=graphite,
            github=github,
            plan_store=PlannedPRBackend(github, github.issues, time=FakeTime()),
        )

        result = runner.invoke(
            set_pr_description,
            ["--title", "New title", "--body", "New body"],
            obj=ctx,
        )

        assert result.exit_code == 0, result.output

        assert len(github.updated_pr_bodies) == 1
        _, updated_body = github.updated_pr_bodies[0]
        assert "plan-header" in updated_body
        # No self-closing reference for draft PR backend
        assert "Closes #" not in updated_body


def test_body_file_option() -> None:
    """Body can be provided via --body-file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git, graphite, github = _make_standard_fakes(env)

        ctx = build_workspace_test_context(env, git=git, graphite=graphite, github=github)

        # Write body to a file
        body_file = env.cwd / "body.md"
        body_file.write_text("Body from file content.", encoding="utf-8")

        result = runner.invoke(
            set_pr_description,
            ["--title", "File body title", "--body-file", str(body_file)],
            obj=ctx,
        )

        assert result.exit_code == 0, result.output

        _, updated_body = github.updated_pr_bodies[0]
        assert "Body from file content." in updated_body
