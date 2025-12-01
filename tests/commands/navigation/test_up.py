"""Tests for erk up command."""

from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.abc import WorktreeInfo
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata

from erk.cli.cli import cli
from erk.core.git.fake import FakeGit
from erk.core.repo_discovery import RepoContext
from tests.test_utils.cli_helpers import assert_cli_error
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


def test_up_with_existing_worktree() -> None:
    """Test up command when child branch has a worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # The test runs from cwd, so we simulate being in feature-1 by setting
        # cwd's current branch to feature-1
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            current_branches={
                env.cwd: "feature-1",  # Simulate being in feature-1 worktree
            },
            default_branches={env.cwd: "main"},
            git_common_dirs={
                env.cwd: env.git_dir,
            },
        )

        # Set up stack: main -> feature-1 -> feature-2
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, repo=repo, use_graphite=True
        )

        # Navigate up from feature-1 to feature-2
        result = runner.invoke(cli, ["up", "--script"], obj=test_ctx, catch_exceptions=False)

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0
        # Should generate script for feature-2 (verify in-memory)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(repo_dir / "worktrees" / "feature-2") in script_content


def test_up_at_top_of_stack() -> None:
    """Test up command when at the top of stack (no children)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-2"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-2"},  # Simulate being in feature-2 worktree
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up stack: main -> feature-1 -> feature-2 (at top)
        FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo, use_graphite=True)

        result = runner.invoke(cli, ["up"], obj=test_ctx, catch_exceptions=False)

        assert_cli_error(result, 1, "Already at the top of the stack")


def test_up_child_has_no_worktree() -> None:
    """Test up command when child branch exists but has no worktree - should auto-create."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Only feature-1 has a worktree, feature-2 does not (will be auto-created)
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},  # Simulate being in feature-1 worktree
            git_common_dirs={env.cwd: env.git_dir},
            # feature-2 exists locally
            local_branches={env.cwd: ["main", "feature-1", "feature-2"]},
        )

        # Set up stack: main -> feature-1 -> feature-2
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir,
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(cli, ["up", "--script"], obj=test_ctx, catch_exceptions=False)

        # Should succeed and create worktree
        assert result.exit_code == 0

        # Verify worktree was created for feature-2
        # added_worktrees is a list of (path, branch) tuples
        assert any(branch == "feature-2" for _path, branch in git_ops.added_worktrees)


def test_up_graphite_not_enabled() -> None:
    """Test up command requires Graphite to be enabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        # Graphite is NOT enabled
        test_ctx = env.build_context(git=git_ops, repo=repo)

        result = runner.invoke(cli, ["up"], obj=test_ctx, catch_exceptions=False)

        assert_cli_error(
            result,
            1,
            "requires Graphite to be enabled",
            "erk config set use_graphite true",
        )


def test_up_detached_head() -> None:
    """Test up command fails gracefully on detached HEAD."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Current branch is None (detached HEAD)
        git_ops = FakeGit(
            worktrees=env.build_worktrees(None),
            current_branches={env.cwd: None},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(git=git_ops, repo=repo, use_graphite=True)

        result = runner.invoke(cli, ["up"], obj=test_ctx, catch_exceptions=False)

        assert_cli_error(result, 1, "Not currently on a branch", "detached HEAD")


def test_up_script_flag() -> None:
    """Test up command with --script flag generates activation script."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},  # Simulate being in feature-1 worktree
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up stack: main -> feature-1 -> feature-2
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(cli, ["up", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Output should be a script path (verify in-memory)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        # Verify script contains the target worktree path
        assert str(repo_dir / "worktrees" / "feature-2") in script_content


def test_up_multiple_children_fails_explicitly() -> None:
    """Test up command fails when branch has multiple children."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Set up stack: main -> feature-1 -> [feature-2a, feature-2b]
        # feature-1 has TWO children
        git_ops = FakeGit(
            worktrees=env.build_worktrees(
                "main", ["feature-1", "feature-2a", "feature-2b"], repo_dir=repo_dir
            ),
            current_branches={env.cwd: "feature-1"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2a", "feature-2b"], commit_sha="def456"
                ),
                "feature-2a": BranchMetadata.branch("feature-2a", "feature-1", commit_sha="ghi789"),
                "feature-2b": BranchMetadata.branch("feature-2b", "feature-1", commit_sha="jkl012"),
            }
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(cli, ["up"], obj=test_ctx, catch_exceptions=False)

        assert_cli_error(
            result,
            1,
            "Error: Branch 'feature-1' has multiple children",
            "'feature-2a'",
            "'feature-2b'",
            "erk create",
        )


def test_up_with_mismatched_worktree_name() -> None:
    """Test up command when worktree directory name differs from branch name.

    This is a regression test for the bug where branch names from Graphite navigation
    were passed directly to _activate_worktree(), which expects worktree paths.
    The fix uses find_worktree_for_branch() to resolve branch -> worktree path.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Worktree directories use different naming than branch names
        # Branch: feature/auth -> Worktree: auth-work
        # Branch: feature/auth-tests -> Worktree: auth-tests-work

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=repo_dir / "auth-work", branch="feature/auth", is_root=False),
                    WorktreeInfo(
                        path=repo_dir / "auth-tests-work",
                        branch="feature/auth-tests",
                        is_root=False,
                    ),
                ]
            },
            current_branches={env.cwd: "feature/auth"},  # Simulate being in feature/auth worktree
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up stack: main -> feature/auth -> feature/auth-tests
        # Branch names contain slashes, but worktree dirs don't
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk(
                    "main", children=["feature/auth"], commit_sha="abc123"
                ),
                "feature/auth": BranchMetadata.branch(
                    "feature/auth", "main", children=["feature/auth-tests"], commit_sha="def456"
                ),
                "feature/auth-tests": BranchMetadata.branch(
                    "feature/auth-tests", "feature/auth", commit_sha="ghi789"
                ),
            }
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, repo=repo, use_graphite=True
        )

        # Navigate up from feature/auth to feature/auth-tests
        # This would fail before the fix because it would try to find a worktree named
        # "feature/auth-tests" instead of resolving to "auth-tests-work"
        result = runner.invoke(cli, ["up", "--script"], obj=test_ctx, catch_exceptions=False)

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Should generate script for auth-tests-work (not feature/auth-tests) - verify in-memory
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(repo_dir / "auth-tests-work") in script_content


def test_up_delete_current_no_children() -> None:
    """Test --delete-current fails when at top of stack (no children)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},  # At top of stack
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            file_statuses={env.cwd: ([], [], [])},
        )

        # Set up stack: main -> feature-1 (at top, no children)
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            }
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(
            cli, ["up", "--delete-current"], obj=test_ctx, catch_exceptions=False
        )

        # Assert: Command failed with error about being at top of stack
        assert_cli_error(
            result, 1, "Cannot navigate up: already at top of stack", "gt branch delete"
        )

        # Assert: No worktrees or branches were deleted
        assert len(git_ops.removed_worktrees) == 0
        assert len(git_ops.deleted_branches) == 0


def test_up_delete_current_multiple_children() -> None:
    """Test --delete-current fails when multiple child branches exist."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Set up stack: main -> feature-1 -> [feature-2a, feature-2b]
        git_ops = FakeGit(
            worktrees=env.build_worktrees(
                "main", ["feature-1", "feature-2a", "feature-2b"], repo_dir=repo_dir
            ),
            current_branches={env.cwd: "feature-1"},  # Has multiple children
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            file_statuses={env.cwd: ([], [], [])},
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2a", "feature-2b"], commit_sha="def456"
                ),
                "feature-2a": BranchMetadata.branch("feature-2a", "feature-1", commit_sha="ghi789"),
                "feature-2b": BranchMetadata.branch("feature-2b", "feature-1", commit_sha="jkl012"),
            }
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(
            cli, ["up", "--delete-current"], obj=test_ctx, catch_exceptions=False
        )

        # Assert: Command failed with error about multiple children
        assert_cli_error(result, 1, "Cannot navigate up: multiple child branches exist", "gt up")

        # Assert: No worktrees or branches were deleted
        assert len(git_ops.removed_worktrees) == 0
        assert len(git_ops.deleted_branches) == 0


def test_up_delete_current_uncommitted_changes() -> None:
    """Test --delete-current blocks when uncommitted changes exist."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            # HAS uncommitted changes
            file_statuses={env.cwd: ([], ["modified.py"], [])},
        )

        # Set up stack: main -> feature-1 -> feature-2
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(
            cli, ["up", "--delete-current"], obj=test_ctx, catch_exceptions=False
        )

        # Assert: Command failed with error about uncommitted changes
        assert_cli_error(
            result, 1, "Cannot delete current branch with uncommitted changes", "commit or stash"
        )

        # Assert: No worktrees or branches were deleted
        assert len(git_ops.removed_worktrees) == 0
        assert len(git_ops.deleted_branches) == 0


def test_up_delete_current_pr_open() -> None:
    """Test --delete-current blocks when PR is still open."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            file_statuses={env.cwd: ([], [], [])},
        )

        # Set up stack: main -> feature-1 -> feature-2
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        # PR for feature-1 is OPEN (active work in progress)
        from erk_shared.github.fake import FakeGitHub
        from erk_shared.github.types import PullRequestInfo

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
            }
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(
            cli, ["up", "--delete-current"], obj=test_ctx, catch_exceptions=False
        )

        # Assert: Command failed with error about PR being open
        assert_cli_error(
            result,
            1,
            "Pull request for branch 'feature-1' is still open",
            "Only closed or merged branches can be deleted",
        )

        # Assert: No worktrees or branches were deleted
        assert len(git_ops.removed_worktrees) == 0
        assert len(git_ops.deleted_branches) == 0


def test_up_delete_current_pr_closed() -> None:
    """Test --delete-current allows deletion when PR is closed (abandoned/rejected)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            file_statuses={env.cwd: ([], [], [])},
        )

        # Set up stack: main -> feature-1 -> feature-2
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        # PR for feature-1 is CLOSED (abandoned/rejected work)
        from erk_shared.github.fake import FakeGitHub
        from erk_shared.github.types import PullRequestInfo

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="CLOSED",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            }
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(
            cli, ["up", "--delete-current", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Assert: Command succeeded - closed PRs are allowed
        assert result.exit_code == 0

        # Assert: Navigated to feature-2
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(repo_dir / "worktrees" / "feature-2") in script_content

        # Assert: feature-1 worktree was removed
        feature_1_path = repo_dir / "worktrees" / "feature-1"
        assert feature_1_path in git_ops.removed_worktrees, "feature-1 worktree should be removed"

        # Assert: feature-1 branch was deleted
        assert "feature-1" in git_ops.deleted_branches


def test_up_delete_current_no_pr() -> None:
    """Test --delete-current warns but proceeds when no PR exists."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            file_statuses={env.cwd: ([], [], [])},
        )

        # Set up stack: main -> feature-1 -> feature-2
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        # No PR for feature-1
        from erk_shared.github.fake import FakeGitHub

        github_ops = FakeGitHub(prs={})

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(
            cli, ["up", "--delete-current"], obj=test_ctx, catch_exceptions=False
        )

        # Assert: Command succeeded with warning about no PR
        exit_msg = f"Expected exit code 0, got {result.exit_code}: {result.output}"
        assert result.exit_code == 0, exit_msg
        assert "Warning:" in result.output
        assert "No pull request found for branch 'feature-1'" in result.output
        assert "Proceeding with deletion without PR verification" in result.output

        # Assert: Branch and worktree were deleted
        assert len(git_ops.removed_worktrees) == 1
        assert len(git_ops.deleted_branches) == 1
        assert "feature-1" in git_ops.deleted_branches


def test_up_delete_current_success() -> None:
    """Test --delete-current flag deletes current branch after navigation."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Set up worktrees: main, feature-1, feature-2
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},  # Currently on feature-1
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            # No uncommitted changes
            file_statuses={env.cwd: ([], [], [])},
        )

        # Set up stack: main -> feature-1 -> feature-2
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        # PR for feature-1 is merged
        from erk_shared.github.fake import FakeGitHub
        from erk_shared.github.types import PullRequestInfo

        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="MERGED",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    title="Feature 1",
                    checks_passing=None,
                    owner="owner",
                    repo="repo",
                    has_conflicts=None,
                ),
            }
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        # Execute: erk up --delete-current --script
        result = runner.invoke(
            cli, ["up", "--delete-current", "--script"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Assert: Navigated to feature-2
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(repo_dir / "worktrees" / "feature-2") in script_content

        # Assert: feature-1 worktree was removed
        feature_1_path = repo_dir / "worktrees" / "feature-1"
        assert feature_1_path in git_ops.removed_worktrees, "feature-1 worktree should be removed"

        # Assert: feature-1 branch was deleted
        assert "feature-1" in git_ops.deleted_branches
