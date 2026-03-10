"""Tests for erk reconcile pipeline and CLI command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands.reconcile_pipeline import (
    ReconcileBranchInfo,
    detect_merged_branches,
    process_merged_branch,
)
from erk_shared.gateway.git.abc import BranchSyncInfo, WorktreeInfo
from erk_shared.gateway.github.types import PRDetails
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.test_utils.env_helpers import erk_inmem_env


def _merged_pr(*, number: int, branch: str, title: str = "Test PR") -> PRDetails:
    """Build a PRDetails in MERGED state for testing."""
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title=title,
        body="",
        state="MERGED",
        is_draft=False,
        base_ref_name="main",
        head_ref_name=branch,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


def _open_pr(*, number: int, branch: str) -> PRDetails:
    """Build a PRDetails in OPEN state for testing."""
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title="Open PR",
        body="",
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


def _closed_pr(*, number: int, branch: str) -> PRDetails:
    """Build a PRDetails in CLOSED (not merged) state for testing."""
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title="Closed PR",
        body="",
        state="CLOSED",
        is_draft=False,
        base_ref_name="main",
        head_ref_name=branch,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


# =============================================================================
# detect_merged_branches
# =============================================================================


def test_detects_merged_branches() -> None:
    """Branches with gone=True and MERGED PRs are detected."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            branch_sync_info={
                env.cwd: {
                    "main": BranchSyncInfo(
                        branch="main", upstream="origin/main", ahead=0, behind=0
                    ),
                    "feature-1": BranchSyncInfo(
                        branch="feature-1",
                        upstream="origin/feature-1",
                        ahead=0,
                        behind=0,
                        gone=True,
                    ),
                }
            },
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )
        github = FakeLocalGitHub(
            prs_by_branch={"feature-1": _merged_pr(number=100, branch="feature-1")},
        )
        ctx = env.build_context(git=git, github=github)

        result = detect_merged_branches(ctx, repo_root=env.cwd, main_repo_root=env.cwd)

        assert len(result) == 1
        assert result[0].branch == "feature-1"
        assert result[0].pr_number == 100


def test_detects_multiple_merged_branches() -> None:
    """Multiple gone+merged branches are all detected."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            branch_sync_info={
                env.cwd: {
                    "main": BranchSyncInfo(
                        branch="main", upstream="origin/main", ahead=0, behind=0
                    ),
                    "feat-a": BranchSyncInfo(
                        branch="feat-a",
                        upstream="origin/feat-a",
                        ahead=0,
                        behind=0,
                        gone=True,
                    ),
                    "feat-b": BranchSyncInfo(
                        branch="feat-b",
                        upstream="origin/feat-b",
                        ahead=0,
                        behind=0,
                        gone=True,
                    ),
                }
            },
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )
        github = FakeLocalGitHub(
            prs_by_branch={
                "feat-a": _merged_pr(number=101, branch="feat-a"),
                "feat-b": _merged_pr(number=102, branch="feat-b"),
            },
        )
        ctx = env.build_context(git=git, github=github)

        result = detect_merged_branches(ctx, repo_root=env.cwd, main_repo_root=env.cwd)

        assert len(result) == 2
        branches = {r.branch for r in result}
        assert branches == {"feat-a", "feat-b"}


def test_skips_closed_not_merged() -> None:
    """Branch with gone=True but PR CLOSED (not merged) is skipped."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            branch_sync_info={
                env.cwd: {
                    "main": BranchSyncInfo(
                        branch="main", upstream="origin/main", ahead=0, behind=0
                    ),
                    "abandoned": BranchSyncInfo(
                        branch="abandoned",
                        upstream="origin/abandoned",
                        ahead=0,
                        behind=0,
                        gone=True,
                    ),
                }
            },
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )
        github = FakeLocalGitHub(
            prs_by_branch={"abandoned": _closed_pr(number=200, branch="abandoned")},
        )
        ctx = env.build_context(git=git, github=github)

        result = detect_merged_branches(ctx, repo_root=env.cwd, main_repo_root=env.cwd)

        assert len(result) == 0


def test_skips_normal_branches() -> None:
    """Branches without gone=True are not detected."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            branch_sync_info={
                env.cwd: {
                    "main": BranchSyncInfo(
                        branch="main", upstream="origin/main", ahead=0, behind=0
                    ),
                    "active": BranchSyncInfo(
                        branch="active",
                        upstream="origin/active",
                        ahead=2,
                        behind=0,
                        gone=False,
                    ),
                }
            },
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )
        github = FakeLocalGitHub(
            prs_by_branch={"active": _merged_pr(number=300, branch="active")},
        )
        ctx = env.build_context(git=git, github=github)

        result = detect_merged_branches(ctx, repo_root=env.cwd, main_repo_root=env.cwd)

        assert len(result) == 0


def test_skips_trunk() -> None:
    """Trunk branch is excluded even if gone=True."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            branch_sync_info={
                env.cwd: {
                    "main": BranchSyncInfo(
                        branch="main",
                        upstream="origin/main",
                        ahead=0,
                        behind=0,
                        gone=True,
                    ),
                }
            },
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )
        ctx = env.build_context(git=git)

        result = detect_merged_branches(ctx, repo_root=env.cwd, main_repo_root=env.cwd)

        assert len(result) == 0


def test_skips_branch_with_no_pr() -> None:
    """Branch with gone=True but no PR on GitHub is skipped."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            branch_sync_info={
                env.cwd: {
                    "main": BranchSyncInfo(
                        branch="main", upstream="origin/main", ahead=0, behind=0
                    ),
                    "no-pr": BranchSyncInfo(
                        branch="no-pr",
                        upstream="origin/no-pr",
                        ahead=0,
                        behind=0,
                        gone=True,
                    ),
                }
            },
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )
        # No PRs configured in FakeLocalGitHub → returns PRNotFound
        github = FakeLocalGitHub()
        ctx = env.build_context(git=git, github=github)

        result = detect_merged_branches(ctx, repo_root=env.cwd, main_repo_root=env.cwd)

        assert len(result) == 0


def test_skips_open_pr() -> None:
    """Branch with gone=True but OPEN PR state is skipped."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            branch_sync_info={
                env.cwd: {
                    "main": BranchSyncInfo(
                        branch="main", upstream="origin/main", ahead=0, behind=0
                    ),
                    "open-pr": BranchSyncInfo(
                        branch="open-pr",
                        upstream="origin/open-pr",
                        ahead=0,
                        behind=0,
                        gone=True,
                    ),
                }
            },
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )
        github = FakeLocalGitHub(
            prs_by_branch={"open-pr": _open_pr(number=400, branch="open-pr")},
        )
        ctx = env.build_context(git=git, github=github)

        result = detect_merged_branches(ctx, repo_root=env.cwd, main_repo_root=env.cwd)

        assert len(result) == 0


def test_nothing_to_reconcile_when_no_gone() -> None:
    """No gone branches at all returns empty list."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            branch_sync_info={
                env.cwd: {
                    "main": BranchSyncInfo(
                        branch="main", upstream="origin/main", ahead=0, behind=0
                    ),
                }
            },
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )
        ctx = env.build_context(git=git)

        result = detect_merged_branches(ctx, repo_root=env.cwd, main_repo_root=env.cwd)

        assert len(result) == 0


def test_fetch_prune_is_called() -> None:
    """detect_merged_branches calls fetch_prune before checking branches."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            branch_sync_info={env.cwd: {}},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )
        ctx = env.build_context(git=git)

        detect_merged_branches(ctx, repo_root=env.cwd, main_repo_root=env.cwd)

        assert len(git.remote.fetch_prune_calls) == 1
        assert git.remote.fetch_prune_calls[0] == (env.cwd, "origin")


def test_detected_branch_includes_metadata() -> None:
    """Detected branch includes PR title, worktree path, and plan/objective info."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        wt_path = env.erk_root / "repos" / env.cwd.name / "worktrees" / "feature-1"
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            branch_sync_info={
                env.cwd: {
                    "main": BranchSyncInfo(
                        branch="main", upstream="origin/main", ahead=0, behind=0
                    ),
                    "feature-1": BranchSyncInfo(
                        branch="feature-1",
                        upstream="origin/feature-1",
                        ahead=0,
                        behind=0,
                        gone=True,
                    ),
                }
            },
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=wt_path, branch="feature-1", is_root=False),
                ]
            },
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )
        github = FakeLocalGitHub(
            prs_by_branch={
                "feature-1": _merged_pr(number=500, branch="feature-1", title="Add feature one")
            },
        )
        ctx = env.build_context(git=git, github=github)

        result = detect_merged_branches(ctx, repo_root=env.cwd, main_repo_root=env.cwd)

        assert len(result) == 1
        info = result[0]
        assert info.branch == "feature-1"
        assert info.pr_number == 500
        assert info.pr_title == "Add feature one"
        assert info.worktree_path == wt_path


# =============================================================================
# process_merged_branch
# =============================================================================


def test_dry_run_no_mutations() -> None:
    """Dry run returns result with all flags false and no mutations."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-1"]},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )
        ctx = env.build_context(git=git)

        info = ReconcileBranchInfo(
            branch="feature-1",
            pr_number=100,
            pr_title="Test",
            worktree_path=None,
            pr_id=None,
            objective_number=None,
        )
        result = process_merged_branch(
            ctx,
            info,
            main_repo_root=env.cwd,
            repo=env.repo,
            cwd=env.cwd,
            dry_run=True,
            skip_learn=False,
        )

        assert result.branch == "feature-1"
        assert result.learn_created is False
        assert result.objective_updated is False
        assert result.cleaned_up is False
        assert result.error is None
        # No branches should be deleted
        assert len(git.deleted_branches) == 0


def test_cleans_up_branch() -> None:
    """Branch is deleted during processing (no plan, no objective)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-1"]},
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main", is_root=True)]},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )
        ctx = env.build_context(git=git)

        info = ReconcileBranchInfo(
            branch="feature-1",
            pr_number=100,
            pr_title="Test",
            worktree_path=None,
            pr_id=None,
            objective_number=None,
        )
        result = process_merged_branch(
            ctx,
            info,
            main_repo_root=env.cwd,
            repo=env.repo,
            cwd=env.cwd,
            dry_run=False,
            skip_learn=False,
        )

        assert result.cleaned_up is True
        assert result.error is None
        assert "feature-1" in git.deleted_branches


def test_cleans_up_worktree() -> None:
    """Linked worktree is removed during cleanup."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        wt_path = env.erk_root / "repos" / env.cwd.name / "worktrees" / "feature-1"
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-1"]},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=wt_path, branch="feature-1", is_root=False),
                ]
            },
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )
        ctx = env.build_context(git=git)

        info = ReconcileBranchInfo(
            branch="feature-1",
            pr_number=100,
            pr_title="Test",
            worktree_path=wt_path,
            pr_id=None,
            objective_number=None,
        )
        result = process_merged_branch(
            ctx,
            info,
            main_repo_root=env.cwd,
            repo=env.repo,
            cwd=env.cwd,
            dry_run=False,
            skip_learn=False,
        )

        assert result.cleaned_up is True
        # Verify worktree was removed
        assert len(git.removed_worktrees) >= 1


def test_cleanup_skips_branch_not_in_local() -> None:
    """If branch no longer exists locally, cleanup is a no-op (success)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},  # feature-1 already deleted
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )
        ctx = env.build_context(git=git)

        info = ReconcileBranchInfo(
            branch="feature-1",
            pr_number=100,
            pr_title="Test",
            worktree_path=None,
            pr_id=None,
            objective_number=None,
        )
        result = process_merged_branch(
            ctx,
            info,
            main_repo_root=env.cwd,
            repo=env.repo,
            cwd=env.cwd,
            dry_run=False,
            skip_learn=False,
        )

        assert result.cleaned_up is True
        assert result.error is None
        # No deletion attempted since branch isn't in local_branches
        assert len(git.deleted_branches) == 0


def test_skip_learn_flag() -> None:
    """With skip_learn=True, learn PR is not created even with plan_id."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-1"]},
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main", is_root=True)]},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )
        ctx = env.build_context(git=git)

        info = ReconcileBranchInfo(
            branch="feature-1",
            pr_number=100,
            pr_title="Test",
            worktree_path=None,
            pr_id="999",
            objective_number=None,
        )
        result = process_merged_branch(
            ctx,
            info,
            main_repo_root=env.cwd,
            repo=env.repo,
            cwd=env.cwd,
            dry_run=False,
            skip_learn=True,
        )

        assert result.learn_created is False
        assert result.cleaned_up is True


# =============================================================================
# CLI integration tests
# =============================================================================


def test_cli_nothing_to_reconcile() -> None:
    """CLI outputs 'Nothing to reconcile' when no gone branches exist."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            branch_sync_info={
                env.cwd: {
                    "main": BranchSyncInfo(
                        branch="main", upstream="origin/main", ahead=0, behind=0
                    ),
                }
            },
            repository_roots={env.cwd: env.cwd},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )
        ctx = env.build_context(git=git)

        result = runner.invoke(cli, ["reconcile"], obj=ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert "Nothing to reconcile" in result.output


def test_cli_dry_run() -> None:
    """CLI with --dry-run shows candidates but makes no changes."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            branch_sync_info={
                env.cwd: {
                    "main": BranchSyncInfo(
                        branch="main", upstream="origin/main", ahead=0, behind=0
                    ),
                    "feature-1": BranchSyncInfo(
                        branch="feature-1",
                        upstream="origin/feature-1",
                        ahead=0,
                        behind=0,
                        gone=True,
                    ),
                }
            },
            local_branches={env.cwd: ["main", "feature-1"]},
            repository_roots={env.cwd: env.cwd},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )
        github = FakeLocalGitHub(
            prs_by_branch={
                "feature-1": _merged_pr(number=100, branch="feature-1"),
            },
        )
        ctx = env.build_context(git=git, github=github)

        result = runner.invoke(cli, ["reconcile", "--dry-run"], obj=ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert "dry run" in result.output.lower()
        # No branches should be deleted
        assert len(git.deleted_branches) == 0


def test_cli_force_processes_without_prompt() -> None:
    """CLI with --force processes branches without confirmation prompt."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            branch_sync_info={
                env.cwd: {
                    "main": BranchSyncInfo(
                        branch="main", upstream="origin/main", ahead=0, behind=0
                    ),
                    "feature-1": BranchSyncInfo(
                        branch="feature-1",
                        upstream="origin/feature-1",
                        ahead=0,
                        behind=0,
                        gone=True,
                    ),
                }
            },
            local_branches={env.cwd: ["main", "feature-1"]},
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main", is_root=True)]},
            repository_roots={env.cwd: env.cwd},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )
        github = FakeLocalGitHub(
            prs_by_branch={
                "feature-1": _merged_pr(number=100, branch="feature-1"),
            },
        )
        ctx = env.build_context(git=git, github=github)

        result = runner.invoke(cli, ["reconcile", "--force"], obj=ctx, catch_exceptions=False)

        assert result.exit_code == 0
        assert "feature-1" in git.deleted_branches
        assert "reconciled" in result.output.lower() or "complete" in result.output.lower()
