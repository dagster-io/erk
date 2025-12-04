"""Tests for erk pr land command."""

from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PullRequestInfo
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata

from erk.cli.commands.pr import pr_group
from erk.core.repo_discovery import RepoContext
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

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0

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


def test_pr_land_error_from_execute_land_pr() -> None:
    """Test pr land shows error when parent is not trunk."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # feature-1 has parent develop (not trunk), which should cause error
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        # Configure feature-1 to have parent "develop" (not trunk "main")
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", commit_sha="abc123"),
                "develop": BranchMetadata.branch(
                    "develop", "main", children=["feature-1"], commit_sha="bcd234"
                ),
                "feature-1": BranchMetadata.branch("feature-1", "develop", commit_sha="def456"),
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

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx, catch_exceptions=False)

        assert_cli_error(result, 1, "Branch must be exactly one level up from main")

        # Verify no cleanup happened
        assert len(git_ops.removed_worktrees) == 0
        assert len(git_ops.deleted_branches) == 0


def test_pr_land_requires_graphite() -> None:
    """Test pr land requires Graphite to be enabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Graphite is NOT enabled
        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(pr_group, ["land"], obj=test_ctx, catch_exceptions=False)

        assert_cli_error(
            result, 1, "requires Graphite to be enabled", "erk config set use_graphite true"
        )


def test_pr_land_requires_clean_working_tree() -> None:
    """Test pr land blocks when uncommitted changes exist."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            # HAS uncommitted changes
            file_statuses={env.cwd: ([], ["modified.py"], [])},
        )

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

        result = runner.invoke(pr_group, ["land"], obj=test_ctx, catch_exceptions=False)

        assert_cli_error(
            result, 1, "Cannot delete current branch with uncommitted changes", "commit or stash"
        )


def test_pr_land_detached_head() -> None:
    """Test pr land fails gracefully on detached HEAD."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        from erk_shared.git.abc import WorktreeInfo

        # Detached HEAD: root worktree has branch=None
        worktrees = {env.cwd: [WorktreeInfo(path=env.cwd, branch=None, is_root=True)]}
        git_ops = FakeGit(
            worktrees=worktrees,
            current_branches={env.cwd: None},
            git_common_dirs={env.cwd: env.git_dir},
            file_statuses={env.cwd: ([], [], [])},
        )

        test_ctx = env.build_context(git=git_ops, use_graphite=True)

        result = runner.invoke(pr_group, ["land"], obj=test_ctx, catch_exceptions=False)

        assert_cli_error(result, 1, "Not currently on a branch", "detached HEAD")


def test_pr_land_with_trunk_in_worktree() -> None:
    """Test pr land navigates to trunk worktree (not root repo)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Trunk has a dedicated worktree (not in root)
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["main", "feature-1"], repo_dir=repo_dir),
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

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0

        # Verify cleanup happened
        assert len(git_ops.removed_worktrees) == 1
        assert "feature-1" in git_ops.deleted_branches


def test_pr_land_no_script_flag_fails_fast() -> None:
    """Test pr land without --script fails before any destructive operations.

    When shell integration is bypassed (e.g., via alias), we fail fast BEFORE
    merging the PR or deleting the worktree, because:
    - A subprocess cannot change the parent shell's cwd
    - The shell would be stranded in the deleted worktree directory
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

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(pr_group, ["land"], obj=test_ctx, catch_exceptions=False)

        # Should fail with clear error about needing shell integration
        assert result.exit_code == 1
        assert "requires shell integration" in result.output
        assert "source <(erk pr land --script)" in result.output

        # CRITICAL: No destructive operations should have happened
        assert len(github_ops.merged_prs) == 0, "PR should NOT be merged without shell integration"
        assert len(git_ops.removed_worktrees) == 0, "Worktree should NOT be deleted"
        assert len(git_ops.deleted_branches) == 0, "Branch should NOT be deleted"


def test_pr_land_error_no_pr_found() -> None:
    """Test pr land shows specific error when no PR exists."""
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

        # No PRs configured - branch has no PR
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

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx, catch_exceptions=False)

        assert_cli_error(result, 1, "No pull request found")


def test_pr_land_error_pr_not_open() -> None:
    """Test pr land shows error when PR is not open."""
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

        # PR is already MERGED (not OPEN)
        github_ops = FakeGitHub(
            prs={
                "feature-1": PullRequestInfo(
                    number=123,
                    state="MERGED",  # Not OPEN
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

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx, catch_exceptions=False)

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

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0

        # Verify safe_chdir was NOT called (it's ineffective, shell integration handles cd)
        assert len(git_ops.chdir_history) == 0, (
            "Should NOT call safe_chdir (activation script handles cd)"
        )


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

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(
            pr_group, ["land", "--up", "--script"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Verify cleanup happened
        feature_1_path = repo_dir / "worktrees" / "feature-1"
        assert feature_1_path in git_ops.removed_worktrees
        assert "feature-1" in git_ops.deleted_branches

        # Verify pull was called on feature-2
        assert len(git_ops.pulled_branches) >= 1

        # Verify activation script was generated for feature-2
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        # The script should point to feature-2 worktree
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

        # feature-1 has NO children
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

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(
            pr_group, ["land", "--up", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Should fail because no children exist
        assert_cli_error(result, 1, "Already at the top of the stack", "no child branches")

        # Verify cleanup did NOT happen since we failed during navigation
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

        # feature-1 has TWO children
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

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(
            pr_group, ["land", "--up", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Should fail because multiple children exist
        assert_cli_error(result, 1, "multiple children")

        # Verify cleanup did NOT happen since we failed during navigation
        assert len(git_ops.removed_worktrees) == 0
        assert len(git_ops.deleted_branches) == 0


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
            local_branches={env.cwd: ["main", "feature-1", "feature-2"]},
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

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(
            pr_group, ["land", "--up", "--script"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Verify feature-1 was cleaned up
        feature_1_path = repo_dir / "worktrees" / "feature-1"
        assert feature_1_path in git_ops.removed_worktrees
        assert "feature-1" in git_ops.deleted_branches

        # Verify activation script was generated for feature-2
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        feature_2_path = repo_dir / "worktrees" / "feature-2"
        assert str(feature_2_path) in script_content
