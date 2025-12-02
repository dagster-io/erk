"""Tests for erk up and erk down navigation."""

from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


def test_up_with_existing_worktree() -> None:
    """Test 'erk up' navigation when child branch has a worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

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
    """Test 'erk up' navigation when at the top of stack (no children)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-2"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-2"},  # Simulate being in feature-2 worktree
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up stack: main -> feature-1 -> feature-2 (at top)
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        test_ctx = env.build_context(git=git_ops, graphite=graphite_ops, use_graphite=True)

        result = runner.invoke(cli, ["up"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "Already at the top of the stack" in result.stderr


def test_up_child_has_no_worktree() -> None:
    """Test 'erk up' navigation when child has no worktree - should auto-create."""
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


def test_down_with_existing_worktree() -> None:
    """Test 'erk down' navigation when parent branch has a worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-2"},  # Simulate being in feature-2 worktree
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

        result = runner.invoke(cli, ["down", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Should generate script for feature-1
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(repo_dir / "worktrees" / "feature-1") in script_content


def test_down_to_trunk_root() -> None:
    """Test 'erk down' navigation when parent is trunk checked out in root."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Main is checked out in root, feature-1 has its own worktree
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},  # Simulate being in feature-1 worktree
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up stack: main -> feature-1
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
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

        # Switch down from feature-1 to root (main)
        result = runner.invoke(cli, ["down", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Should generate script for root
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(env.cwd) in script_content
        assert "root" in script_content.lower()


def test_down_at_trunk() -> None:
    """Test 'erk down' navigation when already at trunk."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up stack: main (only trunk)
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", commit_sha="abc123"),
            }
        )

        test_ctx = env.build_context(git=git_ops, graphite=graphite_ops, use_graphite=True)

        result = runner.invoke(cli, ["down"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "Already at the bottom of the stack" in result.stderr
        assert "trunk branch 'main'" in result.stderr


def test_down_parent_has_no_worktree() -> None:
    """Test 'erk down' navigation when parent has no worktree - should auto-create."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Only feature-2 has a worktree, feature-1 does not (will be auto-created)
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-2"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-2"},  # Simulate being in feature-2 worktree
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            # feature-1 exists locally
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

        result = runner.invoke(cli, ["down", "--script"], obj=test_ctx, catch_exceptions=False)

        # Should succeed and create worktree
        assert result.exit_code == 0

        # Verify worktree was created for feature-1
        # added_worktrees is a list of (path, branch) tuples
        assert any(branch == "feature-1" for _path, branch in git_ops.added_worktrees)


def test_up_down_graphite_not_enabled() -> None:
    """Test 'erk up' and 'erk down' require Graphite to be enabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Graphite is NOT enabled
        graphite_ops = FakeGraphite()

        test_ctx = env.build_context(git=git_ops, graphite=graphite_ops)

        # Try 'erk up'
        result = runner.invoke(cli, ["up"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "requires Graphite to be enabled" in result.stderr
        assert "erk config set use_graphite true" in result.stderr

        # Try 'erk down'
        result = runner.invoke(cli, ["down"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "requires Graphite to be enabled" in result.stderr


def test_up_detached_head() -> None:
    """Test 'erk up' fails gracefully on detached HEAD."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Current branch is None (detached HEAD)
        git_ops = FakeGit(
            worktrees=env.build_worktrees(None),
            current_branches={env.cwd: None},
            git_common_dirs={env.cwd: env.git_dir},
        )

        graphite_ops = FakeGraphite()

        test_ctx = env.build_context(git=git_ops, graphite=graphite_ops, use_graphite=True)

        result = runner.invoke(cli, ["up"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "Not currently on a branch" in result.stderr
        assert "detached HEAD" in result.stderr


def test_up_with_mismatched_worktree_name() -> None:
    """Test 'erk up' when worktree directory name differs from branch name.

    This is a regression test for the bug where branch names from Graphite navigation
    were passed directly to _activate_worktree(), which expects worktree paths.
    The fix uses find_worktree_for_branch() to resolve branch -> worktree path.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Worktree directories use different naming than branch names
        # Branch: feature/db -> Worktree: db-refactor
        # Branch: feature/db-tests -> Worktree: db-tests-implementation
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=repo_dir / "db-refactor", branch="feature/db", is_root=False),
                    WorktreeInfo(
                        path=repo_dir / "db-tests-implementation",
                        branch="feature/db-tests",
                        is_root=False,
                    ),
                ]
            },
            current_branches={env.cwd: "feature/db"},  # Simulate being in feature/db worktree
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up stack: main -> feature/db -> feature/db-tests
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature/db"], commit_sha="abc123"),
                "feature/db": BranchMetadata.branch(
                    "feature/db", "main", children=["feature/db-tests"], commit_sha="def456"
                ),
                "feature/db-tests": BranchMetadata.branch(
                    "feature/db-tests", "feature/db", commit_sha="ghi789"
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

        # Navigate up from feature/db to feature/db-tests using 'erk up'
        # This would fail before the fix because it would try to find a worktree named
        # "feature/db-tests" instead of resolving to "db-tests-implementation"
        result = runner.invoke(cli, ["up", "--script"], obj=test_ctx, catch_exceptions=False)

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Should generate script for db-tests-implementation (not feature/db-tests)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(repo_dir / "db-tests-implementation") in script_content


def test_down_with_mismatched_worktree_name() -> None:
    """Test 'erk down' when worktree directory name differs from branch name.

    This is a regression test for the bug where branch names from Graphite navigation
    were passed directly to _activate_worktree(), which expects worktree paths.
    The fix uses find_worktree_for_branch() to resolve branch -> worktree path.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Worktree directories use different naming than branch names
        # Branch: feature/api -> Worktree: api-work
        # Branch: feature/api-v2 -> Worktree: api-v2-work
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=repo_dir / "api-work", branch="feature/api", is_root=False),
                    WorktreeInfo(
                        path=repo_dir / "api-v2-work", branch="feature/api-v2", is_root=False
                    ),
                ]
            },
            # Simulate being in feature/api-v2 worktree
            current_branches={env.cwd: "feature/api-v2"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up stack: main -> feature/api -> feature/api-v2
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature/api"], commit_sha="abc123"),
                "feature/api": BranchMetadata.branch(
                    "feature/api", "main", children=["feature/api-v2"], commit_sha="def456"
                ),
                "feature/api-v2": BranchMetadata.branch(
                    "feature/api-v2", "feature/api", commit_sha="ghi789"
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

        # Navigate down from feature/api-v2 to feature/api using 'erk down'
        # This would fail before the fix because it would try to find a worktree named
        # "feature/api" instead of resolving to "api-work"
        result = runner.invoke(cli, ["down", "--script"], obj=test_ctx, catch_exceptions=False)

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Should generate script for api-work (not feature/api)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(repo_dir / "api-work") in script_content
