"""Tests for erk pr sync command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _make_pr_info(
    number: int,
    branch: str,
    state: str = "OPEN",
    title: str | None = None,
) -> PullRequestInfo:
    """Create a PullRequestInfo for testing."""
    return PullRequestInfo(
        number=number,
        state=state,
        url=f"https://github.com/owner/repo/pull/{number}",
        is_draft=False,
        title=title or f"PR #{number}",
        checks_passing=True,
        owner="owner",
        repo="repo",
    )


def _make_pr_details(
    number: int,
    head_ref_name: str,
    state: str = "OPEN",
    base_ref_name: str = "main",
    title: str | None = None,
    body: str = "",
    is_cross_repository: bool = False,
) -> PRDetails:
    """Create a PRDetails for testing."""
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title=f"PR #{number}" if title is None else title,
        body=body,
        state=state,
        is_draft=False,
        base_ref_name=base_ref_name,
        head_ref_name=head_ref_name,
        is_cross_repository=is_cross_repository,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


def test_pr_sync_tracks_squashes_restacks_and_submits(tmp_path: Path) -> None:
    """Test successful sync flow: track → squash → update commit → restack → submit."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Setup PR info for branch lookup
        pr_info = _make_pr_info(123, "feature-branch", title="Feature PR")
        pr_details = _make_pr_details(
            number=123,
            head_ref_name="feature-branch",
            title="Add awesome feature",
            body="This PR adds an awesome feature.",
        )
        github = FakeGitHub(
            prs={"feature-branch": pr_info},
            pr_details={123: pr_details},
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

        # Setup FakeClaudeExecutor for auto-restack
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

        assert result.exit_code == 0
        assert "Base branch: main" in result.output
        assert "Branch tracked with Graphite" in result.output
        assert "Squashed commits into 1" in result.output
        assert "Commit message updated" in result.output
        assert "/erk:auto-restack" in result.output
        assert "synchronized with Graphite" in result.output

        # Verify track was called with correct arguments
        assert len(graphite.track_branch_calls) == 1
        assert graphite.track_branch_calls[0] == (env.cwd, "feature-branch", "main")

        # Verify squash was called (execute_squash calls graphite.squash_branch_idempotent)
        assert len(graphite.squash_branch_calls) == 1
        assert graphite.squash_branch_calls[0][0] == env.cwd

        # Verify commit message was updated from PR
        assert len(git.commits) == 1
        assert git.commits[0][1] == "Add awesome feature\n\nThis PR adds an awesome feature."

        # Verify auto-restack was called via ClaudeExecutor
        assert len(claude_executor.executed_commands) == 1
        command, worktree_path, dangerous, _verbose = claude_executor.executed_commands[0]
        assert command == "/erk:auto-restack"
        assert worktree_path == env.cwd
        assert dangerous is True

        # Verify submit was called with force=True (needed after squashing)
        assert len(graphite.submit_stack_calls) == 1
        repo_root, publish, restack, quiet, force = graphite.submit_stack_calls[0]
        assert repo_root == env.cwd
        assert force is True  # Required because squashing rewrites history


def test_pr_sync_succeeds_silently_when_already_tracked(tmp_path: Path) -> None:
    """Test idempotent behavior when branch is already tracked."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Setup PR info
        pr_info = _make_pr_info(123, "feature-branch", title="Feature PR")
        pr_details = _make_pr_details(
            number=123,
            head_ref_name="feature-branch",
            title="Feature PR",
        )
        github = FakeGitHub(
            prs={"feature-branch": pr_info},
            pr_details={123: pr_details},
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

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

        assert result.exit_code == 0
        assert "already tracked by Graphite" in result.output
        assert "parent: main" in result.output

        # Should NOT call track/squash/restack/submit
        assert len(graphite.track_branch_calls) == 0
        assert len(graphite.squash_branch_calls) == 0
        assert len(graphite.restack_calls) == 0
        assert len(graphite.submit_stack_calls) == 0


def test_pr_sync_requires_dangerous_flag(tmp_path: Path) -> None:
    """Test that sync fails when --dangerous flag is not provided."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
        )

        ctx = build_workspace_test_context(env, git=git)

        result = runner.invoke(pr_group, ["sync"], obj=ctx)

        assert result.exit_code != 0
        assert "Missing option '--dangerous'" in result.output


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

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

        assert result.exit_code == 1
        assert "Not on a branch" in result.output


def test_pr_sync_fails_when_no_pr_exists(tmp_path: Path) -> None:
    """Test error when branch has no PR."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # No PR for this branch (empty prs dict)
        github = FakeGitHub(prs={}, pr_details={})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "no-pr-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

        assert result.exit_code == 1
        assert "No pull request found for branch 'no-pr-branch'" in result.output


def test_pr_sync_fails_when_pr_is_closed(tmp_path: Path) -> None:
    """Test error when PR is closed."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # PR is closed
        pr_info = _make_pr_info(456, "closed-branch", state="CLOSED", title="Closed PR")
        pr_details = _make_pr_details(
            number=456,
            head_ref_name="closed-branch",
            state="CLOSED",
            title="Closed PR",
        )
        github = FakeGitHub(
            prs={"closed-branch": pr_info},
            pr_details={456: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "closed-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

        assert result.exit_code == 1
        assert "Cannot sync CLOSED PR" in result.output


def test_pr_sync_fails_when_pr_is_merged(tmp_path: Path) -> None:
    """Test error when PR is merged."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # PR is merged
        pr_info = _make_pr_info(789, "merged-branch", state="MERGED", title="Merged PR")
        pr_details = _make_pr_details(
            number=789,
            head_ref_name="merged-branch",
            state="MERGED",
            title="Merged PR",
        )
        github = FakeGitHub(
            prs={"merged-branch": pr_info},
            pr_details={789: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "merged-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

        assert result.exit_code == 1
        assert "Cannot sync MERGED PR" in result.output


def test_pr_sync_fails_when_cross_repo_fork(tmp_path: Path) -> None:
    """Test error when PR is from a fork (cross-repository)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # PR exists and is open
        pr_info = _make_pr_info(999, "fork-branch", title="Fork PR")

        # But it's a cross-repository fork
        pr_details = _make_pr_details(
            number=999,
            head_ref_name="fork-branch",
            title="Fork PR",
            is_cross_repository=True,  # This is the key check
        )

        github = FakeGitHub(
            prs={"fork-branch": pr_info},
            pr_details={999: pr_details},
        )

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "fork-branch"},
        )

        ctx = build_workspace_test_context(env, git=git, github=github)

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

        assert result.exit_code == 1
        assert "Cannot sync fork PRs" in result.output
        assert "Graphite cannot track branches from forks" in result.output


def test_pr_sync_handles_squash_single_commit(tmp_path: Path) -> None:
    """Test sync handles single-commit case gracefully (no squash needed)."""
    import subprocess

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Setup PR
        pr_info = _make_pr_info(111, "single-commit-branch", title="Single Commit")
        pr_details = _make_pr_details(
            number=111,
            head_ref_name="single-commit-branch",
            title="Single Commit",
        )
        github = FakeGitHub(
            prs={"single-commit-branch": pr_info},
            pr_details={111: pr_details},
        )

        # Configure gt squash to return "nothing to squash" (Graphite sees single commit)
        nothing_to_squash_error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["gt", "squash"],
            stderr="ERROR: Only one commit in branch, nothing to squash.",
        )
        graphite = FakeGraphite(
            branches={},
            squash_branch_raises=nothing_to_squash_error,
        )

        # Single commit ahead - squash_branch_idempotent handles "nothing to squash"
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "single-commit-branch"},
            commits_ahead={(env.cwd, "main"): 1},  # Single commit
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

        # Should succeed - squash_branch_idempotent handles "nothing to squash" gracefully
        assert result.exit_code == 0
        assert "Already a single commit, no squash needed" in result.output
        assert "synchronized with Graphite" in result.output

        # Verify squash WAS called (idempotent method handles single commit case)
        assert len(graphite.squash_branch_calls) == 1


def test_pr_sync_handles_submit_failure_gracefully(tmp_path: Path) -> None:
    """Test sync continues when submit fails (non-critical)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Setup PR
        pr_info = _make_pr_info(222, "feature-branch", title="Feature")
        pr_details = _make_pr_details(
            number=222,
            head_ref_name="feature-branch",
            title="Feature",
        )
        github = FakeGitHub(
            prs={"feature-branch": pr_info},
            pr_details={222: pr_details},
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

        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

        # Submit failure should fail the command
        assert result.exit_code == 1
        assert "network error" in str(result.exception)


def test_pr_sync_squash_raises_unexpected_error(tmp_path: Path) -> None:
    """Test sync fails when squash raises unexpected error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Setup PR
        pr_info = _make_pr_info(333, "feature-branch", title="Feature")
        pr_details = _make_pr_details(
            number=333,
            head_ref_name="feature-branch",
            title="Feature",
        )
        github = FakeGitHub(
            prs={"feature-branch": pr_info},
            pr_details={333: pr_details},
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

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

        # Should fail with error message from execute_squash
        assert result.exit_code == 1
        assert "Failed to squash" in result.output


def test_pr_sync_uses_correct_base_branch(tmp_path: Path) -> None:
    """Test sync uses PR base branch from GitHub, not assumptions."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # PR targets "release/v1.0" not "main"
        pr_info = _make_pr_info(444, "hotfix-branch", title="Hotfix")
        pr_details = _make_pr_details(
            number=444,
            head_ref_name="hotfix-branch",
            base_ref_name="release/v1.0",  # Non-standard base
            title="Hotfix",
        )
        github = FakeGitHub(
            prs={"hotfix-branch": pr_info},
            pr_details={444: pr_details},
        )

        graphite = FakeGraphite(branches={})

        # Note: commits_ahead uses the trunk branch detected by git, not PR base
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "hotfix-branch"},
            commits_ahead={(env.cwd, "main"): 2},  # Commits ahead of detected trunk
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

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

        # Setup PR with title but NO body (empty string)
        pr_info = _make_pr_info(555, "title-only-branch", title="Title Only PR")
        pr_details = _make_pr_details(
            number=555,
            head_ref_name="title-only-branch",
            title="Just a title",
            body="",  # No body
        )
        github = FakeGitHub(
            prs={"title-only-branch": pr_info},
            pr_details={555: pr_details},
        )

        graphite = FakeGraphite(branches={})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "title-only-branch"},
            commits_ahead={(env.cwd, "main"): 2},  # Commits to squash
        )
        git._commits.append((env.cwd, "Original message", []))

        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

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

        # Setup PR with empty title
        pr_info = _make_pr_info(666, "no-title-branch", title=None)
        pr_details = _make_pr_details(
            number=666,
            head_ref_name="no-title-branch",
            title="",  # Empty title
        )
        github = FakeGitHub(
            prs={"no-title-branch": pr_info},
            pr_details={666: pr_details},
        )

        graphite = FakeGraphite(branches={})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "no-title-branch"},
            commits_ahead={(env.cwd, "main"): 2},  # Commits to squash
        )
        git._commits.append((env.cwd, "Original message", []))

        # Setup FakeClaudeExecutor
        claude_executor = FakeClaudeExecutor(claude_available=True)

        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

        assert result.exit_code == 0
        # Should NOT update commit message
        assert "Commit message updated" not in result.output

        # Original message should be preserved
        assert len(git.commits) == 1
        assert git.commits[0][1] == "Original message"


def test_pr_sync_fails_when_claude_not_available(tmp_path: Path) -> None:
    """Test sync fails when Claude CLI is not available."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Setup PR
        pr_info = _make_pr_info(777, "feature-branch", title="Feature")
        pr_details = _make_pr_details(
            number=777,
            head_ref_name="feature-branch",
            title="Feature",
        )
        github = FakeGitHub(
            prs={"feature-branch": pr_info},
            pr_details={777: pr_details},
        )

        graphite = FakeGraphite(branches={})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 2},
        )
        git._commits.append((env.cwd, "Original message", []))

        # Claude NOT available
        claude_executor = FakeClaudeExecutor(claude_available=False)

        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

        assert result.exit_code == 1
        assert "Claude CLI not found" in result.output
        assert "https://claude.com/download" in result.output


def test_pr_sync_fails_when_auto_restack_requires_interactive(tmp_path: Path) -> None:
    """Test sync fails when auto-restack detects semantic conflict."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Setup PR
        pr_info = _make_pr_info(888, "feature-branch", title="Feature")
        pr_details = _make_pr_details(
            number=888,
            head_ref_name="feature-branch",
            title="Feature",
        )
        github = FakeGitHub(
            prs={"feature-branch": pr_info},
            pr_details={888: pr_details},
        )

        graphite = FakeGraphite(branches={})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 2},
        )
        git._commits.append((env.cwd, "Original message", []))

        # Auto-restack will require interactive resolution (semantic conflict)
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            simulated_tool_events=["AskUserQuestion: How should we resolve this conflict?"],
        )

        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

        assert result.exit_code == 1
        assert "Semantic conflict requires interactive resolution" in result.output


def test_pr_sync_fails_when_auto_restack_fails(tmp_path: Path) -> None:
    """Test sync fails when auto-restack command fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        env.setup_repo_structure()

        # Setup PR
        pr_info = _make_pr_info(999, "feature-branch", title="Feature")
        pr_details = _make_pr_details(
            number=999,
            head_ref_name="feature-branch",
            title="Feature",
        )
        github = FakeGitHub(
            prs={"feature-branch": pr_info},
            pr_details={999: pr_details},
        )

        graphite = FakeGraphite(branches={})

        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: "feature-branch"},
            commits_ahead={(env.cwd, "main"): 2},
        )
        git._commits.append((env.cwd, "Original message", []))

        # Auto-restack will fail
        claude_executor = FakeClaudeExecutor(claude_available=True, command_should_fail=True)

        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, claude_executor=claude_executor
        )

        result = runner.invoke(pr_group, ["sync", "--dangerous"], obj=ctx)

        assert result.exit_code == 1
        assert "/erk:auto-restack failed" in result.output
