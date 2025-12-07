"""Tests for erk pr land command.

The pr land command now:
1. Merges the PR
2. Automatically runs extraction (unless --skip-insights)
3. Prints extraction issue URL (if successful)
4. Deletes worktree and navigates to trunk

Note on extraction plans:
PRs that originate from extraction plans (plan_type: "extraction") automatically
skip insight extraction. This prevents infinite loops where extracting insights
from an extraction-originated PR would lead to another extraction plan.
"""

from dataclasses import replace
from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.types import PRDetails, PullRequestInfo
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata
from erk_shared.integrations.gt.operations.finalize import ERK_SKIP_EXTRACTION_LABEL
from erk_shared.scratch.markers import PENDING_EXTRACTION_MARKER, marker_exists

from erk.cli.commands.pr import pr_group
from erk.cli.commands.pr.land_cmd import is_extraction_origin_pr
from erk.core.repo_discovery import RepoContext
from tests.test_utils.cli_helpers import assert_cli_error
from tests.test_utils.env_helpers import erk_inmem_env


def test_pr_land_success_runs_extraction_and_deletes_worktree() -> None:
    """Test pr land merges PR, runs extraction, deletes worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_1_path = repo_dir / "worktrees" / "feature-1"

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
            pr_details={
                123: PRDetails(
                    number=123,
                    url="https://github.com/owner/repo/pull/123",
                    title="Feature 1",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature-1",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
            merge_should_succeed=True,
        )

        # FakeGitHubIssues for extraction
        issues_ops = FakeGitHubIssues(username="testuser")

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )
        # Manually set issues since build_context doesn't have issues param
        test_ctx = replace(test_ctx, issues=issues_ops)

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0

        # Verify PR was merged
        assert 123 in github_ops.merged_prs

        # Verify worktree WAS removed (new behavior)
        assert feature_1_path in git_ops.removed_worktrees

        # Verify branch WAS deleted (new behavior)
        assert "feature-1" in git_ops.deleted_branches

        # Verify activation script points to root repo (trunk)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(repo.root) in script_content

        # Verify "Deleted worktree" message
        assert "Deleted worktree and branch" in result.output


def test_pr_land_extraction_failure_continues() -> None:
    """Test pr land continues with worktree deletion even if extraction fails."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_1_path = repo_dir / "worktrees" / "feature-1"

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
            pr_details={
                123: PRDetails(
                    number=123,
                    url="https://github.com/owner/repo/pull/123",
                    title="Feature 1",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature-1",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
            merge_should_succeed=True,
        )

        # FakeGitHubIssues with no username = not authenticated = extraction fails
        issues_ops = FakeGitHubIssues(username=None)

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )
        test_ctx = replace(test_ctx, issues=issues_ops)

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx, catch_exceptions=False)

        # Should succeed overall despite extraction failure
        assert result.exit_code == 0

        # Verify PR was merged
        assert 123 in github_ops.merged_prs

        # Verify extraction failure warning shown
        assert "Extraction failed" in result.output

        # Verify worktree still deleted despite extraction failure
        assert feature_1_path in git_ops.removed_worktrees
        assert "feature-1" in git_ops.deleted_branches


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


def test_pr_land_no_script_flag_fails_fast() -> None:
    """Test pr land without --script fails before any operations.

    When shell integration is bypassed (e.g., via alias), we fail fast BEFORE
    merging the PR, because:
    - Shell integration is required for activation script output
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
            pr_details={
                123: PRDetails(
                    number=123,
                    url="https://github.com/owner/repo/pull/123",
                    title="Feature 1",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature-1",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
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

        # CRITICAL: No operations should have happened
        assert len(github_ops.merged_prs) == 0, "PR should NOT be merged without shell integration"


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
            pr_details={
                123: PRDetails(
                    number=123,
                    url="https://github.com/owner/repo/pull/123",
                    title="Feature 1",
                    body="",
                    state="MERGED",  # Not OPEN
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature-1",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
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
            pr_details={
                123: PRDetails(
                    number=123,
                    url="https://github.com/owner/repo/pull/123",
                    title="Feature 1",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature-1",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
            merge_should_succeed=True,
        )

        issues_ops = FakeGitHubIssues(username="testuser")

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )
        test_ctx = replace(test_ctx, issues=issues_ops)

        result = runner.invoke(pr_group, ["land", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0

        # Verify safe_chdir was NOT called (it's ineffective, shell integration handles cd)
        assert len(git_ops.chdir_history) == 0, (
            "Should NOT call safe_chdir (activation script handles cd)"
        )


def test_pr_land_with_skip_insights_deletes_worktree_and_branch() -> None:
    """Test pr land --skip-insights merges PR, deletes worktree/branch, goes to trunk."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_1_path = repo_dir / "worktrees" / "feature-1"

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
            pr_details={
                123: PRDetails(
                    number=123,
                    url="https://github.com/owner/repo/pull/123",
                    title="Feature 1",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature-1",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
            merge_should_succeed=True,
        )

        # Note: No issues setup needed since --skip-insights skips extraction
        issues_ops = FakeGitHubIssues(username="testuser")

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )
        test_ctx = replace(test_ctx, issues=issues_ops)

        result = runner.invoke(
            pr_group, ["land", "--script", "--skip-insights"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Verify PR was merged
        assert 123 in github_ops.merged_prs

        # Verify NO extraction was attempted (no issues created)
        assert len(issues_ops.created_issues) == 0

        # Verify worktree was removed
        assert feature_1_path in git_ops.removed_worktrees

        # Verify branch was deleted
        assert "feature-1" in git_ops.deleted_branches

        # Verify output messages
        assert "Deleted worktree and branch" in result.output

        # Verify activation script points to root repo (not worktree)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(repo.root) in script_content

        # Verify extraction-related output NOT shown
        assert "Extracted insights" not in result.output
        assert "Extraction failed" not in result.output


def test_pr_land_extraction_origin_skips_marker_and_deletes_worktree() -> None:
    """Test pr land auto-skips insights for PRs with erk-skip-extraction label.

    When a PR has the erk-skip-extraction label, erk pr land should:
    1. NOT create the pending-extraction marker
    2. Delete the worktree and branch (like --skip-insights)
    3. Navigate to trunk

    This prevents infinite extraction loops from extraction-originated PRs.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_1_path = repo_dir / "worktrees" / "feature-1"

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
            pr_details={
                123: PRDetails(
                    number=123,
                    url="https://github.com/owner/repo/pull/123",
                    title="Feature 1",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature-1",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
            merge_should_succeed=True,
        )
        # PR has erk-skip-extraction label
        github_ops.set_pr_labels(123, {ERK_SKIP_EXTRACTION_LABEL})

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

        # Verify PR was merged
        assert 123 in github_ops.merged_prs

        # Verify NO pending extraction marker was created
        assert not marker_exists(feature_1_path, PENDING_EXTRACTION_MARKER)

        # Verify worktree was removed
        assert feature_1_path in git_ops.removed_worktrees

        # Verify branch was deleted
        assert "feature-1" in git_ops.deleted_branches

        # Verify user was informed about skipping extraction
        assert "extraction plan" in result.output
        assert "skipping insight extraction" in result.output

        # Verify output messages about deletion
        assert "Deleted worktree and branch" in result.output


def test_is_extraction_origin_pr_returns_true_when_label_present(tmp_path: Path) -> None:
    """Test is_extraction_origin_pr returns True when PR has erk-skip-extraction label."""
    from erk.core.context import ErkContext

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    github_ops = FakeGitHub()
    # PR has erk-skip-extraction label
    github_ops.set_pr_labels(456, {ERK_SKIP_EXTRACTION_LABEL})

    ctx = ErkContext.for_test(
        cwd=repo_root,
        github=github_ops,
    )

    result = is_extraction_origin_pr(ctx, repo_root, 456)

    assert result is True


def test_is_extraction_origin_pr_returns_false_when_label_absent(tmp_path: Path) -> None:
    """Test is_extraction_origin_pr returns False when PR has no erk-skip-extraction label."""
    from erk.core.context import ErkContext

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    github_ops = FakeGitHub()
    # PR has other labels, but not erk-skip-extraction
    github_ops.set_pr_labels(456, {"bug", "enhancement"})

    ctx = ErkContext.for_test(
        cwd=repo_root,
        github=github_ops,
    )

    result = is_extraction_origin_pr(ctx, repo_root, 456)

    assert result is False


def test_is_extraction_origin_pr_returns_false_when_no_labels(tmp_path: Path) -> None:
    """Test is_extraction_origin_pr returns False when PR has no labels."""
    from erk.core.context import ErkContext

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # No labels configured for this PR
    github_ops = FakeGitHub()

    ctx = ErkContext.for_test(
        cwd=repo_root,
        github=github_ops,
    )

    result = is_extraction_origin_pr(ctx, repo_root, 456)

    assert result is False


def test_pr_land_with_up_navigates_to_child_branch() -> None:
    """Test --up navigates to child branch after landing."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_1_path = repo_dir / "worktrees" / "feature-1"
        feature_2_path = repo_dir / "worktrees" / "feature-2"

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            repository_roots={env.cwd: env.cwd},
            file_statuses={env.cwd: ([], [], [])},
        )

        # feature-1 is parent of feature-2 (feature-1 has one child)
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
            pr_details={
                123: PRDetails(
                    number=123,
                    url="https://github.com/owner/repo/pull/123",
                    title="Feature 1",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature-1",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
            merge_should_succeed=True,
        )

        issues_ops = FakeGitHubIssues(username="testuser")

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )
        test_ctx = replace(test_ctx, issues=issues_ops)

        result = runner.invoke(
            pr_group, ["land", "--script", "--up"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Verify PR was merged
        assert 123 in github_ops.merged_prs

        # Verify worktree of feature-1 was removed
        assert feature_1_path in git_ops.removed_worktrees

        # Verify branch feature-1 was deleted
        assert "feature-1" in git_ops.deleted_branches

        # Verify activation script points to feature-2 worktree (the child)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(feature_2_path) in script_content


def test_pr_land_with_up_no_children_fails_before_merge() -> None:
    """Test --up fails BEFORE merge when no children exist."""
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
            pr_details={
                123: PRDetails(
                    number=123,
                    url="https://github.com/owner/repo/pull/123",
                    title="Feature 1",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature-1",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
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
            pr_group, ["land", "--script", "--up"], obj=test_ctx, catch_exceptions=False
        )

        # Should fail with exit code 1
        assert result.exit_code == 1

        # Should show error about no children
        assert "Cannot use --up" in result.output
        assert "has no children" in result.output
        assert "Use 'erk pr land' without --up" in result.output

        # CRITICAL: PR should NOT have been merged (fail-fast)
        assert len(github_ops.merged_prs) == 0


def test_pr_land_with_up_uses_main_repo_root_after_worktree_deletion() -> None:
    """Test --up uses main_repo_root (not deleted worktree path) for navigation.

    This regression test verifies fix for issue where repo.root pointed to the
    deleted worktree directory. After deletion, find_worktree_for_branch() was
    called with the stale repo.root path, causing worktree lookup to fail.

    The fix creates post_deletion_repo with root=main_repo_root before navigation.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_1_path = repo_dir / "worktrees" / "feature-1"
        feature_2_path = repo_dir / "worktrees" / "feature-2"

        # Key setup: worktrees are keyed by env.cwd (main repo root)
        # This simulates running from inside a linked worktree
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            # Current branch is feature-1, being run from feature-1 worktree
            current_branches={feature_1_path: "feature-1"},
            default_branches={env.cwd: "main"},
            git_common_dirs={feature_1_path: env.git_dir, env.cwd: env.git_dir},
            # CRITICAL: repository_root for feature_1_path must return feature_1_path
            # (the worktree path itself), not the main repo root. This simulates
            # how git --show-toplevel returns the worktree path when inside a worktree.
            repository_roots={feature_1_path: feature_1_path, env.cwd: env.cwd},
            file_statuses={feature_1_path: ([], [], [])},
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
            pr_details={
                123: PRDetails(
                    number=123,
                    url="https://github.com/owner/repo/pull/123",
                    title="Feature 1",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature-1",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
            merge_should_succeed=True,
        )

        issues_ops = FakeGitHubIssues(username="testuser")

        # CRITICAL: repo.root is the worktree path (that will be deleted)
        # repo.main_repo_root is the main repo root (env.cwd)
        # After worktree deletion, only main_repo_root is valid for worktree lookups
        repo = RepoContext(
            root=feature_1_path,  # Worktree path being deleted!
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            main_repo_root=env.cwd,  # Main repo root (stays valid)
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            repo=repo,
            use_graphite=True,
            cwd=feature_1_path,  # Running from worktree
        )
        test_ctx = replace(test_ctx, issues=issues_ops)

        # Without the fix: find_worktree_for_branch(feature_1_path, "feature-2")
        # would fail because feature_1_path is no longer in any worktree list
        # after deletion.
        #
        # With the fix: find_worktree_for_branch(main_repo_root, "feature-2")
        # succeeds because main_repo_root is the dict key for worktrees.
        result = runner.invoke(
            pr_group, ["land", "--script", "--up"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # Verify PR was merged
        assert 123 in github_ops.merged_prs

        # Verify worktree of feature-1 was removed
        assert feature_1_path in git_ops.removed_worktrees

        # Verify branch feature-1 was deleted
        assert "feature-1" in git_ops.deleted_branches

        # Verify activation script points to feature-2 worktree (the child)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(feature_2_path) in script_content

        # CRITICAL: Verify no new worktree was created for feature-2
        # The bug was that find_worktree_for_branch couldn't find the existing
        # worktree, causing it to unnecessarily create a new one.
        # With the fix, the existing worktree should be found directly.
        assert len(git_ops.added_worktrees) == 0, (
            "Should find existing worktree, not create a new one. "
            f"Added worktrees: {git_ops.added_worktrees}"
        )


def test_pr_land_with_up_multiple_children_fails_before_merge() -> None:
    """Test --up fails BEFORE merge when multiple children exist."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

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

        # feature-1 has MULTIPLE children
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
            pr_details={
                123: PRDetails(
                    number=123,
                    url="https://github.com/owner/repo/pull/123",
                    title="Feature 1",
                    body="PR body",
                    state="OPEN",
                    is_draft=False,
                    base_ref_name="main",
                    head_ref_name="feature-1",
                    is_cross_repository=False,
                    mergeable="MERGEABLE",
                    merge_state_status="CLEAN",
                    owner="owner",
                    repo="repo",
                )
            },
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
            pr_group, ["land", "--script", "--up"], obj=test_ctx, catch_exceptions=False
        )

        # Should fail with exit code 1
        assert result.exit_code == 1

        # Should show error about multiple children
        assert "Cannot use --up" in result.output
        assert "has multiple children" in result.output
        assert "'feature-2a'" in result.output
        assert "'feature-2b'" in result.output
        assert "erk co <branch>" in result.output

        # CRITICAL: PR should NOT have been merged (fail-fast)
        assert len(github_ops.merged_prs) == 0
