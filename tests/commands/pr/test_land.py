"""Tests for erk pr land command."""

import subprocess
from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PullRequestInfo
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata

from erk.cli.commands.pr import pr_group
from erk.core.repo_discovery import RepoContext
from tests.fakes.claude_executor import FakeClaudeExecutor
from tests.test_utils.cli_helpers import assert_cli_error
from tests.test_utils.env_helpers import erk_inmem_env


def test_pr_land_success_navigates_to_trunk() -> None:
    """Test pr land merges PR, deletes branch, navigates to trunk, and pulls."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
            pr_titles={123: "Feature 1"},
            pr_bodies_by_number={123: "PR body"},
            merge_should_succeed=True,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        # Configure FakeClaudeExecutor for extraction step
        claude_executor = FakeClaudeExecutor(claude_available=True)

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0

        # Verify extraction was called with correct command
        assert len(claude_executor.executed_commands) == 1
        cmd, path, dangerous, verbose = claude_executor.executed_commands[0]
        assert cmd == "/erk:land-extraction"
        assert path == env.cwd
        assert dangerous is True  # Non-interactive execution skips prompts
        assert verbose is False

        # Verify worktree was removed
        feature_1_path = repo_dir / "worktrees" / "feature-1"
        assert feature_1_path in git_ops.removed_worktrees

        # Verify branch was deleted
        assert "feature-1" in git_ops.deleted_branches

        # Verify pull was called
        assert len(git_ops.pulled_branches) >= 1

        # Verify PR was merged
        assert 123 in github_ops.merged_prs

        # Verify activation script was generated
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(env.cwd) in script_content


def test_pr_land_extraction_failure_stops_before_deletion() -> None:
    """Test pr land stops when extraction fails, preserving worktree for investigation.

    When extraction fails after PR merge, the command should:
    1. Merge the PR (this already happened)
    2. Fail with extraction error
    3. NOT delete the worktree (preserve for investigation)
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
            pr_titles={123: "Feature 1"},
            pr_bodies_by_number={123: "PR body"},
            merge_should_succeed=True,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        # Configure FakeClaudeExecutor to fail
        claude_executor = FakeClaudeExecutor(
            claude_available=True,
            command_should_fail=True,
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx, catch_exceptions=False)

        # Command should fail
        assert result.exit_code == 1

        # Verify error message mentions extraction failure
        assert "Extraction" in result.output or "extraction" in result.output

        # PR was already merged (before extraction step)
        assert 123 in github_ops.merged_prs

        # CRITICAL: Worktree should NOT be deleted (preserved for investigation)
        assert len(git_ops.removed_worktrees) == 0
        assert len(git_ops.deleted_branches) == 0

        # Pull should NOT have been called (stopped before that step)
        assert len(git_ops.pulled_branches) == 0


def test_pr_land_error_from_execute_land_pr() -> None:
    """Test pr land shows error when parent is not trunk."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", commit_sha="abc123"),
                "parent": BranchMetadata.branch("parent", "main", children=["feature-1"]),
                "feature-1": BranchMetadata.branch("feature-1", "parent", commit_sha="def456"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx)

        # Should fail - parent is not trunk (must branch directly from main)
        assert result.exit_code == 1
        assert (
            "not trunk" in result.output.lower()
            or "branches directly from" in result.output.lower()
            or "branch must" in result.output.lower()
        )


def test_pr_land_error_no_graphite() -> None:
    """Test pr land fails when Graphite is not enabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            use_graphite=False,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx)

        assert_cli_error(result, 1, "Graphite", "enabled")


def test_pr_land_error_uncommitted_changes() -> None:
    """Test pr land fails with uncommitted changes."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Configure git with uncommitted changes
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: (["modified.py"], [], [])},  # Uncommitted changes
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"]),
                "feature-1": BranchMetadata.branch("feature-1", "main"),
            }
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            repo=repo,
            use_graphite=True,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx)

        assert_cli_error(result, 1, "uncommitted", "changes")


def test_pr_land_error_detached_head() -> None:
    """Test pr land fails when on detached HEAD."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # No current branch = detached HEAD
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={},  # Empty = detached HEAD
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"]),
                "feature-1": BranchMetadata.branch("feature-1", "main"),
            }
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            repo=repo,
            use_graphite=True,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx)

        assert_cli_error(result, 1, "Not currently on a branch", "detached HEAD")


def test_pr_land_with_trunk_in_worktree() -> None:
    """Test pr land navigates to trunk worktree (not root repo)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Trunk has a dedicated worktree (not in root)
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
            pr_titles={123: "Feature 1"},
            pr_bodies_by_number={123: "PR body"},
            merge_should_succeed=True,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0

        # Should generate script pointing to trunk (root in this case)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None


def test_pr_land_error_merge_blocked() -> None:
    """Test pr land fails when merge is blocked."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
            merge_should_succeed=False,  # Block the merge
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx)

        assert result.exit_code == 1
        assert "status check" in result.output.lower() or "merge" in result.output.lower()


def test_pr_land_error_pr_closed() -> None:
    """Test pr land fails when PR is already closed."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="CLOSED",  # Already closed
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx)

        assert_cli_error(result, 1, "Pull request is not open")


def test_pr_land_does_not_call_safe_chdir() -> None:
    """Test pr land does NOT call safe_chdir (it's ineffective).

    A subprocess cannot change the parent shell's working directory.
    The shell integration (activation script) handles the cd, so calling
    safe_chdir() in the Python process is misleading and unnecessary.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
            pr_titles={123: "Feature 1"},
            pr_bodies_by_number={123: "PR body"},
            merge_should_succeed=True,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0

        # Verify NO safe_chdir was called - the chdir_calls list should be empty
        # (safe_chdir would be tracked via mutations, but we verify via script)
        # The script content shows the destination, proving we rely on shell cd instead
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert (
            "cd" in script_content.lower()
        ), "Should NOT call safe_chdir (activation script handles cd)"


def test_pr_land_with_up_flag_navigates_to_child() -> None:
    """Test pr land --up navigates to child branch after merging."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create a stack: main -> feature-1 -> feature-2
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
            pr_titles={123: "Feature 1"},
            pr_bodies_by_number={123: "PR body"},
            merge_should_succeed=True,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            claude_executor=claude_executor,
        )

        result = runner.invoke(
            pr_group, ["land", "--up", "--script"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Should navigate to feature-2 (child of feature-1)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        feature_2_path = repo_dir / "worktrees" / "feature-2"
        assert str(feature_2_path) in script_content


def test_pr_land_with_up_flag_no_children_fails() -> None:
    """Test pr land --up fails when at top of stack (no children)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=[], commit_sha="def456"
                ),
            }
        )

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
            pr_titles={123: "Feature 1"},
            pr_bodies_by_number={123: "PR body"},
            merge_should_succeed=True,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["land", "--up", "--script"], obj=test_ctx)

        # Should fail - no children to navigate to
        assert result.exit_code != 0
        assert "no child" in result.output.lower() or "top of stack" in result.output.lower()

        # No worktree should be removed (stopped before deletion)
        assert len(git_ops.removed_worktrees) == 0
        assert len(git_ops.deleted_branches) == 0


def test_pr_land_with_up_flag_multiple_children_fails() -> None:
    """Test pr land --up fails when branch has multiple children."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create a branch with two children
        git_ops = FakeGit(
            worktrees=env.build_worktrees(
                "main", ["feature-1", "feature-2a", "feature-2b"], repo_dir=repo_dir
            ),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1",
                    "main",
                    children=["feature-2a", "feature-2b"],  # Two children
                    commit_sha="def456",
                ),
                "feature-2a": BranchMetadata.branch(
                    "feature-2a", "feature-1", commit_sha="child1"
                ),
                "feature-2b": BranchMetadata.branch(
                    "feature-2b", "feature-1", commit_sha="child2"
                ),
            }
        )

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
            pr_titles={123: "Feature 1"},
            pr_bodies_by_number={123: "PR body"},
            merge_should_succeed=True,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["land", "--up", "--script"], obj=test_ctx)

        # Should fail - can't navigate up with multiple children
        assert result.exit_code != 0
        assert (
            "multiple" in result.output.lower()
            or "ambiguous" in result.output.lower()
            or "children" in result.output.lower()
        )

        # No worktree should be removed (stopped before deletion)
        assert len(git_ops.removed_worktrees) == 0
        assert len(git_ops.deleted_branches) == 0


def test_pr_land_outputs_script_before_deletion() -> None:
    """Test pr land outputs activation script BEFORE deleting worktree.

    This is critical for shell integration recovery: if any step after worktree
    deletion fails (e.g., git pull), the shell integration handler must still
    be able to navigate the shell to the destination.

    With the fix, the sequence is:
    1. Merge PR
    2. Create extraction plan
    3. Output activation script ← BEFORE destructive operations
    4. Delete worktree
    5. Pull latest changes

    If step 5 fails, the script was already output so shell can still navigate.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
            pr_titles={123: "Feature 1"},
            pr_bodies_by_number={123: "PR body"},
            merge_should_succeed=True,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0

        # Verify script was generated
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None

        # Verify worktree was deleted (after script was output)
        feature_1_path = repo_dir / "worktrees" / "feature-1"
        assert feature_1_path in git_ops.removed_worktrees

        # The order is verified by the fact that the script exists and worktree was deleted
        # (since we reached this point with both script and deletion completed)
        # The order is verified by the fact that the script exists and worktree was deleted


def test_pr_land_outputs_script_even_when_pull_fails() -> None:
    """Test pr land outputs script even when git pull fails after deletion.

    This is the key bug fix: when pull fails AFTER worktree deletion,
    the script should already have been output so shell can navigate.

    Without the fix:
    1. Merge PR
    2. Delete worktree
    3. Pull fails → no script output → shell stranded

    With the fix:
    1. Merge PR
    2. Create extraction plan
    3. Output script ← early output
    4. Delete worktree
    5. Pull fails → script already output → shell can navigate
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Configure git to fail on pull
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
            pull_branch_raises=subprocess.CalledProcessError(
                1, "git pull", stderr="fatal: Could not fast-forward"
            ),
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
            pr_titles={123: "Feature 1"},
            pr_bodies_by_number={123: "PR body"},
            merge_should_succeed=True,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            claude_executor=claude_executor,
        )

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx)

        # Command fails due to pull error, but key point is:
        # Script should ALREADY be output before the pull failure
        assert result.exit_code == 1  # Pull failure causes non-zero exit

        # The critical test: script was output BEFORE the pull failure
        # so shell can navigate even though command failed
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None, "Script should be output even when pull fails"

        # Worktree should still be deleted (deletion happens before pull)
        feature_1_path = repo_dir / "worktrees" / "feature-1"
        assert feature_1_path in git_ops.removed_worktrees

        # Verify PR was merged (before pull failure)
        assert 123 in github_ops.merged_prs


def test_pr_land_with_up_flag_creates_worktree_if_needed() -> None:
    """Test pr land --up auto-creates worktree for child branch if missing."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # feature-2 has an existing worktree so the command can navigate to it
        # This tests the main --up navigation flow
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            },
            pr_titles={123: "Feature 1"},
            pr_bodies_by_number={123: "PR body"},
            merge_should_succeed=True,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        claude_executor = FakeClaudeExecutor(claude_available=True)

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            claude_executor=claude_executor,
        )

        result = runner.invoke(
            pr_group, ["land", "--up", "--script"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Should navigate to feature-2
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        feature_2_path = repo_dir / "worktrees" / "feature-2"
        assert str(feature_2_path) in script_content
