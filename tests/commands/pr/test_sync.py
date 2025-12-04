"""Tests for erk pr sync command."""

from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRCheckoutInfo, PRInfo
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata

from erk.cli.commands.pr import pr_group
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_pr_sync_tracks_squashes_restacks_and_submits(tmp_path: Path) -> None:
    """Test successful sync flow: track → squash → update commit → restack → submit."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Setup PR info with title and body
        pr_info = PRInfo(state="OPEN", pr_number=123, title="Feature PR")
        pr_checkout_info = PRCheckoutInfo(
            number=123,
            head_ref_name="feature-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeGitHub(
            pr_statuses={"feature-branch": pr_info},
            pr_checkout_infos={123: pr_checkout_info},
            pr_bases={123: "main"},
            pr_titles={123: "Add awesome feature"},
            pr_bodies_by_number={123: "This PR adds an awesome feature."},
        )

        # Branch NOT tracked yet (empty branches dict)
        graphite = FakeGraphite(branches={})

        # Set current branch via FakeGit - add a commit so amend has something to modify
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
            existing_paths={env.cwd, env.repo.worktrees_dir},
            commits_ahead={(env.cwd, "main"): 2},  # Multiple commits to squash
        )
        # Simulate an existing commit that will be amended
        git._commits.append((env.cwd, "Original message", []))

        ctx = build_workspace_test_context(env, git=git, github=github, graphite=graphite)

        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        assert result.exit_code == 0
        assert "Base branch: main" in result.output
        assert "Branch tracked with Graphite" in result.output
        assert "Squashed 2 commits into 1" in result.output
        assert "Commit message updated" in result.output
        assert "Restack complete" in result.output
        assert "synchronized with Graphite" in result.output

        # Verify track was called with correct arguments
        assert len(graphite.track_branch_calls) == 1
        assert graphite.track_branch_calls[0] == (env.cwd, "feature-branch", "main")

        # Verify squash was called (execute_squash calls graphite.squash_branch internally)
        assert len(graphite.squash_branch_calls) == 1
        assert graphite.squash_branch_calls[0][0] == env.cwd

        # Verify commit message was updated from PR
        assert len(git.commits) == 1
        assert git.commits[0][1] == "Add awesome feature\n\nThis PR adds an awesome feature."

        # Verify restack was called with no-interactive
        assert len(graphite.restack_calls) == 1
        assert graphite.restack_calls[0] == (env.cwd, True, True)

        # Verify submit was called
        assert len(graphite.submit_stack_calls) == 1
        assert graphite.submit_stack_calls[0][0] == env.cwd


def test_pr_sync_succeeds_silently_when_already_tracked(tmp_path: Path) -> None:
    """Test idempotent behavior when branch is already tracked."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Setup PR info
        pr_info = PRInfo(state="OPEN", pr_number=123, title="Feature PR")
        pr_checkout_info = PRCheckoutInfo(
            number=123,
            head_ref_name="feature-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeGitHub(
            pr_statuses={"feature-branch": pr_info},
            pr_checkout_infos={123: pr_checkout_info},
        )

        # Branch ALREADY tracked (has parent)
        graphite = FakeGraphite(
            branches={
                "feature-branch": BranchMetadata(
                    name="feature-branch",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha="abc123",
                )
            }
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github, graphite=graphite)

        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        assert result.exit_code == 0
        assert "already tracked by Graphite" in result.output
        assert "parent: main" in result.output

        # Should NOT call track/squash/restack/submit
        assert len(graphite.track_branch_calls) == 0
        assert len(graphite.squash_branch_calls) == 0
        assert len(graphite.restack_calls) == 0
        assert len(graphite.submit_stack_calls) == 0


def test_pr_sync_fails_when_not_on_branch(tmp_path: Path) -> None:
    """Test error when on detached HEAD."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Detached HEAD (no current branch)
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: None},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        assert result.exit_code == 1
        assert "Not on a branch" in result.output


def test_pr_sync_fails_when_no_pr_exists(tmp_path: Path) -> None:
    """Test error when branch has no PR."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # No PR for this branch (state = NONE)
        github = FakeGitHub(
            pr_statuses={"no-pr-branch": PRInfo(state="NONE", pr_number=None, title=None)}
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "no-pr-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        assert result.exit_code == 1
        assert "No pull request found for branch 'no-pr-branch'" in result.output


def test_pr_sync_fails_when_pr_is_closed(tmp_path: Path) -> None:
    """Test error when PR is closed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # PR is closed
        pr_info = PRInfo(state="CLOSED", pr_number=456, title="Closed PR")
        github = FakeGitHub(pr_statuses={"closed-branch": pr_info})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "closed-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        assert result.exit_code == 1
        assert "Cannot sync CLOSED PR" in result.output


def test_pr_sync_fails_when_pr_is_merged(tmp_path: Path) -> None:
    """Test error when PR is merged."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # PR is merged
        pr_info = PRInfo(state="MERGED", pr_number=789, title="Merged PR")
        github = FakeGitHub(pr_statuses={"merged-branch": pr_info})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "merged-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        assert result.exit_code == 1
        assert "Cannot sync MERGED PR" in result.output


def test_pr_sync_fails_when_cross_repo_fork(tmp_path: Path) -> None:
    """Test error when PR is from a fork (cross-repository)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # PR exists and is open
        pr_info = PRInfo(state="OPEN", pr_number=999, title="Fork PR")

        # But it's a cross-repository fork
        pr_checkout_info = PRCheckoutInfo(
            number=999,
            head_ref_name="fork-branch",
            is_cross_repository=True,  # This is the key check
            state="OPEN",
        )

        github = FakeGitHub(
            pr_statuses={"fork-branch": pr_info},
            pr_checkout_infos={999: pr_checkout_info},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "fork-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        assert result.exit_code == 1
        assert "Cannot sync fork PRs" in result.output
        assert "Graphite cannot track branches from forks" in result.output


def test_pr_sync_handles_squash_single_commit(tmp_path: Path) -> None:
    """Test sync handles single-commit case gracefully (no squash needed)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Setup PR
        pr_info = PRInfo(state="OPEN", pr_number=111, title="Single Commit")
        pr_checkout_info = PRCheckoutInfo(
            number=111,
            head_ref_name="single-commit-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeGitHub(
            pr_statuses={"single-commit-branch": pr_info},
            pr_checkout_infos={111: pr_checkout_info},
            pr_bases={111: "main"},
        )

        # No squash_branch_raises needed - execute_squash checks commit count first
        graphite = FakeGraphite(branches={})

        # Single commit ahead - execute_squash will skip squashing
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "single-commit-branch"},
            commits_ahead={(env.cwd, "main"): 1},  # Single commit
        )

        ctx = build_workspace_test_context(env, git=git, github=github, graphite=graphite)

        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        # Should succeed - execute_squash detects single commit and skips
        assert result.exit_code == 0
        assert "Already a single commit, no squash needed" in result.output
        assert "synchronized with Graphite" in result.output

        # Verify squash was NOT called (single commit detected beforehand)
        assert len(graphite.squash_branch_calls) == 0


def test_pr_sync_handles_submit_failure_gracefully(tmp_path: Path) -> None:
    """Test sync continues when submit fails (non-critical)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Setup PR
        pr_info = PRInfo(state="OPEN", pr_number=222, title="Feature")
        pr_checkout_info = PRCheckoutInfo(
            number=222,
            head_ref_name="feature-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeGitHub(
            pr_statuses={"feature-branch": pr_info},
            pr_checkout_infos={222: pr_checkout_info},
            pr_bases={222: "main"},
        )

        # Submit raises error
        graphite = FakeGraphite(
            branches={},
            submit_stack_raises=RuntimeError("network error"),
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 2},  # Commits to squash
        )

        ctx = build_workspace_test_context(env, git=git, github=github, graphite=graphite)

        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        # Submit failure should fail the command
        assert result.exit_code == 1
        assert "network error" in str(result.exception)


def test_pr_sync_squash_raises_unexpected_error(tmp_path: Path) -> None:
    """Test sync fails when squash raises unexpected error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Setup PR
        pr_info = PRInfo(state="OPEN", pr_number=333, title="Feature")
        pr_checkout_info = PRCheckoutInfo(
            number=333,
            head_ref_name="feature-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeGitHub(
            pr_statuses={"feature-branch": pr_info},
            pr_checkout_infos={333: pr_checkout_info},
            pr_bases={333: "main"},
        )

        # Squash raises unexpected error via CalledProcessError (what execute_squash catches)
        import subprocess

        error = subprocess.CalledProcessError(1, "gt squash")
        error.stdout = ""
        error.stderr = "unexpected squash error"
        graphite = FakeGraphite(
            branches={},
            squash_branch_raises=error,
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 2},  # Multiple commits to trigger squash
        )

        ctx = build_workspace_test_context(env, git=git, github=github, graphite=graphite)

        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        # Should fail with error message from execute_squash
        assert result.exit_code == 1
        assert "Failed to squash" in result.output


def test_pr_sync_uses_correct_base_branch(tmp_path: Path) -> None:
    """Test sync uses PR base branch from GitHub, not assumptions."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # PR targets "release/v1.0" not "main"
        pr_info = PRInfo(state="OPEN", pr_number=444, title="Hotfix")
        pr_checkout_info = PRCheckoutInfo(
            number=444,
            head_ref_name="hotfix-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeGitHub(
            pr_statuses={"hotfix-branch": pr_info},
            pr_checkout_infos={444: pr_checkout_info},
            pr_bases={444: "release/v1.0"},  # Non-standard base
        )

        graphite = FakeGraphite(branches={})

        # Note: commits_ahead uses the trunk branch detected by git, not PR base
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "hotfix-branch"},
            commits_ahead={(env.cwd, "main"): 2},  # Commits ahead of detected trunk
        )

        ctx = build_workspace_test_context(env, git=git, github=github, graphite=graphite)

        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        assert result.exit_code == 0
        assert "Base branch: release/v1.0" in result.output

        # Verify track used correct parent
        assert len(graphite.track_branch_calls) == 1
        assert graphite.track_branch_calls[0] == (env.cwd, "hotfix-branch", "release/v1.0")


def test_pr_sync_updates_commit_with_title_only(tmp_path: Path) -> None:
    """Test commit message is updated with title only when no body exists."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Setup PR with title but NO body
        pr_info = PRInfo(state="OPEN", pr_number=555, title="Title Only PR")
        pr_checkout_info = PRCheckoutInfo(
            number=555,
            head_ref_name="title-only-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeGitHub(
            pr_statuses={"title-only-branch": pr_info},
            pr_checkout_infos={555: pr_checkout_info},
            pr_bases={555: "main"},
            pr_titles={555: "Just a title"},
            # No pr_bodies_by_number - body is None
        )

        graphite = FakeGraphite(branches={})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "title-only-branch"},
            commits_ahead={(env.cwd, "main"): 2},  # Commits to squash
        )
        git._commits.append((env.cwd, "Original message", []))

        ctx = build_workspace_test_context(env, git=git, github=github, graphite=graphite)

        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        assert result.exit_code == 0
        assert "Commit message updated" in result.output

        # Verify commit message is just the title (no body)
        assert len(git.commits) == 1
        assert git.commits[0][1] == "Just a title"


def test_pr_sync_skips_commit_update_when_no_title(tmp_path: Path) -> None:
    """Test commit message is not updated when PR has no title."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Setup PR with NO title
        pr_info = PRInfo(state="OPEN", pr_number=666, title=None)
        pr_checkout_info = PRCheckoutInfo(
            number=666,
            head_ref_name="no-title-branch",
            is_cross_repository=False,
            state="OPEN",
        )
        github = FakeGitHub(
            pr_statuses={"no-title-branch": pr_info},
            pr_checkout_infos={666: pr_checkout_info},
            pr_bases={666: "main"},
            # No pr_titles - title is None
        )

        graphite = FakeGraphite(branches={})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "no-title-branch"},
            commits_ahead={(env.cwd, "main"): 2},  # Commits to squash
        )
        git._commits.append((env.cwd, "Original message", []))

        ctx = build_workspace_test_context(env, git=git, github=github, graphite=graphite)

        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        assert result.exit_code == 0
        # Should NOT update commit message
        assert "Commit message updated" not in result.output

        # Original message should be preserved
        assert len(git.commits) == 1
        assert git.commits[0][1] == "Original message"
