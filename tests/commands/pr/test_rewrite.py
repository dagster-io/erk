"""Tests for erk pr rewrite command.

These tests verify the CLI layer behavior of the rewrite command.
The command squashes commits, generates an AI-powered commit message,
amends the commit, pushes, and updates the remote PR.
"""

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.gateway.branch_manager.types import SubmitBranchError
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.draft_pr import DraftPRPlanBackend
from erk_shared.plan_store.draft_pr_lifecycle import build_plan_stage_body
from tests.fakes.prompt_executor import FakePromptExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import ErkIsolatedFsEnv, erk_isolated_fs_env
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


def _make_pr_details(
    *,
    number: int,
    branch: str,
    body: str = "",
) -> PRDetails:
    """Create a PRDetails for testing."""
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title="WIP",
        body=body,
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name=branch,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


def _make_rewrite_fakes(
    env: ErkIsolatedFsEnv,
    *,
    branch_name: str,
    pr_number: int = 42,
    pr_body: str = "",
    commits_ahead: int = 3,
    squash_raises: Exception | None = None,
    prompt_output: str = "Add awesome feature\n\nThis PR adds an awesome new feature.",
    prompt_error: str | None = None,
    submit_branch_error: SubmitBranchError | None = None,
) -> tuple[FakeGit, FakeGraphite, FakeGitHub, FakePromptExecutor]:
    """Create standard fakes for rewrite command tests."""
    pr_details = _make_pr_details(number=pr_number, branch=branch_name, body=pr_body)

    git = FakeGit(
        git_common_dirs={env.cwd: env.git_dir},
        repository_roots={env.cwd: env.git_dir},
        local_branches={env.cwd: ["main", branch_name]},
        default_branches={env.cwd: "main"},
        trunk_branches={env.git_dir: "main"},
        current_branches={env.cwd: branch_name},
        commits_ahead={(env.cwd, "main"): commits_ahead},
        diff_to_branch={(env.cwd, "main"): "diff --git a/file.py b/file.py\n+new content"},
    )

    graphite = FakeGraphite(
        authenticated=True,
        squash_branch_raises=squash_raises,
        branches={
            branch_name: BranchMetadata(
                name=branch_name,
                parent="main",
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

    github = FakeGitHub(
        authenticated=True,
        prs_by_branch={branch_name: pr_details},
    )

    executor_kwargs: dict = {"available": True}
    if prompt_error is not None:
        executor_kwargs["simulated_prompt_error"] = prompt_error
    else:
        executor_kwargs["simulated_prompt_output"] = prompt_output
    executor = FakePromptExecutor(**executor_kwargs)

    return git, graphite, github, executor


def test_pr_rewrite_happy_path() -> None:
    """Test successful rewrite: squash, generate, amend, push, update PR."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git, graphite, github, executor = _make_rewrite_fakes(env, branch_name="feature")

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite,
            prompt_executor=executor,
        )

        result = runner.invoke(pr_group, ["rewrite"], obj=ctx)

        assert result.exit_code == 0, result.output
        assert "PR title and description updated" in result.output
        assert "Add awesome feature" in result.output

        # Verify commit was amended
        assert len(git.commits) == 1
        commit_message = git.commits[0].message
        assert "Add awesome feature" in commit_message
        assert "awesome new feature" in commit_message

        # Verify branch was pushed (Graphite submit_stack was called)
        assert "Branch pushed" in result.output

        # Verify PR was updated
        assert len(github.updated_pr_titles) == 1
        assert github.updated_pr_titles[0] == (42, "Add awesome feature")


def test_pr_rewrite_already_single_commit() -> None:
    """Test rewrite with already-single-commit (squash is idempotent)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git, graphite, github, executor = _make_rewrite_fakes(
            env, branch_name="feature", commits_ahead=1
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite,
            prompt_executor=executor,
        )

        result = runner.invoke(pr_group, ["rewrite"], obj=ctx)

        assert result.exit_code == 0, result.output
        assert "PR title and description updated" in result.output


def test_pr_rewrite_fails_when_no_pr() -> None:
    """Test that rewrite fails when no PR exists for the branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature"]},
            default_branches={env.cwd: "main"},
            trunk_branches={env.git_dir: "main"},
            current_branches={env.cwd: "feature"},
            commits_ahead={(env.cwd, "main"): 1},
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
        # No PR configured for the branch
        github = FakeGitHub(authenticated=True)
        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite,
            prompt_executor=executor,
        )

        result = runner.invoke(pr_group, ["rewrite"], obj=ctx)

        assert result.exit_code != 0
        assert "No PR found" in result.output
        assert "erk pr submit" in result.output


def test_pr_rewrite_fails_when_squash_conflicts() -> None:
    """Test that rewrite fails when squash encounters conflicts."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git, graphite, github, executor = _make_rewrite_fakes(
            env,
            branch_name="feature",
            squash_raises=RuntimeError("Squash conflict: resolve manually"),
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite,
            prompt_executor=executor,
        )

        result = runner.invoke(pr_group, ["rewrite"], obj=ctx)

        assert result.exit_code != 0
        assert "Squash failed" in result.output


def test_pr_rewrite_fails_when_ai_generation_fails() -> None:
    """Test that rewrite fails when commit message generation fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git, graphite, github, executor = _make_rewrite_fakes(
            env,
            branch_name="feature",
            prompt_error="Claude CLI execution failed",
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite,
            prompt_executor=executor,
        )

        result = runner.invoke(pr_group, ["rewrite"], obj=ctx)

        assert result.exit_code != 0
        assert "Failed to generate message" in result.output


def test_pr_rewrite_fails_when_detached_head() -> None:
    """Test that rewrite fails when in detached HEAD state."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
            # No current_branches means detached HEAD (get_current_branch returns None)
        )
        executor = FakePromptExecutor(available=True)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["rewrite"], obj=ctx)

        assert result.exit_code != 0
        assert "detached HEAD" in result.output


def test_pr_rewrite_fails_when_claude_not_available() -> None:
    """Test that rewrite fails when Claude CLI is not available."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        executor = FakePromptExecutor(available=False)

        ctx = build_workspace_test_context(env, git=git, prompt_executor=executor)

        result = runner.invoke(pr_group, ["rewrite"], obj=ctx)

        assert result.exit_code != 0
        assert "Claude CLI not found" in result.output


def test_pr_rewrite_discovers_issue_from_impl_folder() -> None:
    """Test that rewrite discovers issue number from .impl/issue.json for footer."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        # Create .impl/issue.json with issue number
        impl_dir = env.cwd / ".impl"
        impl_dir.mkdir()
        (impl_dir / "issue.json").write_text(
            '{"issue_number": 456, "issue_url": "https://github.com/owner/repo/issues/456",'
            ' "created_at": "2026-01-01T00:00:00Z", "synced_at": "2026-01-01T00:00:00Z"}'
        )

        git, graphite, github, executor = _make_rewrite_fakes(
            env,
            branch_name="feature",
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite,
            prompt_executor=executor,
        )

        result = runner.invoke(pr_group, ["rewrite"], obj=ctx)

        assert result.exit_code == 0, result.output

        # Verify the footer includes the discovered issue reference
        assert len(github.updated_pr_bodies) == 1
        updated_body = github.updated_pr_bodies[0][1]
        assert "Closes #456" in updated_body


def test_pr_rewrite_preserves_closing_ref_from_existing_footer() -> None:
    """Test that rewrite preserves closing reference from existing PR footer."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        existing_body = "Old body\n---\n\nCloses #123\n\nTo checkout this PR..."

        git, graphite, github, executor = _make_rewrite_fakes(
            env,
            branch_name="feature",
            pr_body=existing_body,
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite,
            prompt_executor=executor,
        )

        result = runner.invoke(pr_group, ["rewrite"], obj=ctx)

        assert result.exit_code == 0, result.output

        # Verify the PR body was updated and closing ref preserved
        assert len(github.updated_pr_bodies) == 1
        updated_body = github.updated_pr_bodies[0][1]
        assert "Closes #123" in updated_body


def test_pr_rewrite_draft_pr_backend_preserves_metadata() -> None:
    """Test that rewrite preserves metadata prefix and omits Closes # for draft PR backend."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        metadata_body = format_plan_header_body_for_test()
        plan_content = "# My Plan\n\nImplement the thing."
        pr_body = build_plan_stage_body(metadata_body, plan_content)

        git, graphite, github, executor = _make_rewrite_fakes(
            env,
            branch_name="feature",
            pr_body=pr_body,
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            github=github,
            graphite=graphite,
            prompt_executor=executor,
            plan_store=DraftPRPlanBackend(github, github.issues, time=FakeTime()),
        )

        result = runner.invoke(pr_group, ["rewrite"], obj=ctx)

        assert result.exit_code == 0, result.output

        # Verify the PR body preserves metadata prefix
        assert len(github.updated_pr_bodies) == 1
        updated_body = github.updated_pr_bodies[0][1]
        assert "plan-header" in updated_body
        # No self-closing reference for draft PR backend
        assert "Closes #" not in updated_body
