"""Tests for execute_land_stack and helpers.

Tests the stack landing logic that merges an entire Graphite stack bottom-up.
"""

from pathlib import Path

import pytest

from erk.cli.commands.land_stack import (
    StackLandEntry,
    _merge_and_cleanup_branch,
    _rebase_and_push,
    _reparent_upstack,
    _resolve_stack,
    _validate_stack_prs,
    execute_land_stack,
)
from erk.cli.ensure import UserFacingCliError
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.git.abc import BranchDivergence, RebaseResult, WorktreeInfo
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeLocalGitHub
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason
from erk_shared.gateway.graphite.fake import FakeGraphite


def _make_pr_details(
    *,
    pr_number: int,
    branch: str,
    base_ref_name: str = "main",
    state: str = "OPEN",
    title: str | None = None,
) -> PRDetails:
    return PRDetails(
        number=pr_number,
        url=f"https://github.com/owner/repo/pull/{pr_number}",
        title=title if title is not None else f"PR for {branch}",
        body=f"Body for {branch}",
        state=state,
        base_ref_name=base_ref_name,
        head_ref_name=branch,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        is_draft=False,
        is_cross_repository=False,
        owner="owner",
        repo="repo",
    )


def _make_pull_request_info(
    *,
    pr_number: int,
    branch: str,
) -> PullRequestInfo:
    return PullRequestInfo(
        number=pr_number,
        state="OPEN",
        url=f"https://github.com/owner/repo/pull/{pr_number}",
        is_draft=False,
        title=f"PR for {branch}",
        checks_passing=None,
        owner="owner",
        repo="repo",
        head_branch=branch,
    )


def _make_repo(tmp_path: Path) -> RepoContext:
    return RepoContext(
        root=tmp_path,
        repo_name="test-repo",
        repo_dir=tmp_path / ".repo",
        worktrees_dir=tmp_path / ".repo" / "worktrees",
        pool_json_path=tmp_path / ".repo" / "pool.json",
    )


# ============================================================================
# _resolve_stack
# ============================================================================


class TestResolveStack:
    def test_resolves_three_branch_stack(self, tmp_path: Path) -> None:
        """Returns branches to land (trunk stripped)."""
        fake_graphite = FakeGraphite(stacks={"C": ["main", "A", "B", "C"]})
        fake_git = FakeGit(current_branches={tmp_path: "C"})
        ctx = context_for_test(git=fake_git, graphite=fake_graphite, cwd=tmp_path)

        result = _resolve_stack(ctx, tmp_path)
        assert result == ["A", "B", "C"]

    def test_requires_graphite(self, tmp_path: Path) -> None:
        """Errors when Graphite is not enabled."""
        fake_git = FakeGit(current_branches={tmp_path: "feature"})
        ctx = context_for_test(
            git=fake_git,
            graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
            cwd=tmp_path,
        )

        with pytest.raises(UserFacingCliError):
            _resolve_stack(ctx, tmp_path)

    def test_errors_when_no_stack(self, tmp_path: Path) -> None:
        """Errors when branch is not in any stack."""
        fake_graphite = FakeGraphite(stacks={})
        fake_git = FakeGit(current_branches={tmp_path: "orphan"})
        ctx = context_for_test(git=fake_git, graphite=fake_graphite, cwd=tmp_path)

        with pytest.raises(UserFacingCliError):
            _resolve_stack(ctx, tmp_path)


# ============================================================================
# _validate_stack_prs
# ============================================================================


class TestValidateStackPrs:
    def test_validates_all_open_prs(self, tmp_path: Path) -> None:
        """Returns entries for all open PRs in the stack."""
        pr_a = _make_pr_details(pr_number=101, branch="A", base_ref_name="main")
        pr_b = _make_pr_details(pr_number=102, branch="B", base_ref_name="A")

        fake_github = FakeLocalGitHub(prs_by_branch={"A": pr_a, "B": pr_b})
        ctx = context_for_test(github=fake_github, cwd=tmp_path)

        entries = _validate_stack_prs(ctx, tmp_path, ["A", "B"], "main", force=True)

        assert len(entries) == 2
        assert entries[0].branch == "A"
        assert entries[0].pr_number == 101
        assert entries[1].branch == "B"
        assert entries[1].pr_number == 102

    def test_fails_when_pr_not_open(self, tmp_path: Path) -> None:
        """Fails fast if any PR is not open."""
        pr_a = _make_pr_details(pr_number=101, branch="A", state="MERGED")
        fake_github = FakeLocalGitHub(prs_by_branch={"A": pr_a})
        ctx = context_for_test(github=fake_github, cwd=tmp_path)

        with pytest.raises(UserFacingCliError):
            _validate_stack_prs(ctx, tmp_path, ["A"], "main", force=True)

    def test_fails_when_pr_not_found(self, tmp_path: Path) -> None:
        """Fails fast if no PR exists for a branch."""
        fake_github = FakeLocalGitHub()
        ctx = context_for_test(github=fake_github, cwd=tmp_path)

        with pytest.raises(UserFacingCliError):
            _validate_stack_prs(ctx, tmp_path, ["A"], "main", force=True)


# ============================================================================
# _reparent_upstack
# ============================================================================


class TestReparentUpstack:
    def test_updates_pr_bases_and_tracking(self, tmp_path: Path) -> None:
        """Updates PR bases and Graphite tracking for remaining entries."""
        pr_b = _make_pr_details(pr_number=102, branch="B", base_ref_name="A")
        pr_c = _make_pr_details(pr_number=103, branch="C", base_ref_name="B")

        fake_github = FakeLocalGitHub()
        fake_graphite = FakeGraphite(stacks={"B": ["main", "A", "B", "C"]})
        ctx = context_for_test(
            github=fake_github,
            graphite=fake_graphite,
            cwd=tmp_path,
        )

        remaining = [
            StackLandEntry(
                branch="B",
                pr_number=102,
                pr_details=pr_b,
                worktree_path=None,
                plan_id=None,
                objective_number=None,
            ),
            StackLandEntry(
                branch="C",
                pr_number=103,
                pr_details=pr_c,
                worktree_path=None,
                plan_id=None,
                objective_number=None,
            ),
        ]

        _reparent_upstack(ctx, tmp_path, remaining, "main")

        assert (102, "main") in fake_github.updated_pr_bases
        assert (103, "main") in fake_github.updated_pr_bases
        # Graphite tracking updated via linked branch ops
        track_calls = fake_graphite.track_branch_calls
        assert any(b == "B" and p == "main" for _, b, p in track_calls)
        assert any(b == "C" and p == "main" for _, b, p in track_calls)


# ============================================================================
# _merge_and_cleanup_branch
# ============================================================================


class TestMergeAndCleanupBranch:
    def test_merges_and_deletes_remote(self, tmp_path: Path) -> None:
        """Merges PR and deletes remote branch."""
        pr_a = _make_pr_details(pr_number=101, branch="A")
        fake_github = FakeLocalGitHub(
            pr_details={101: pr_a},
            merge_should_succeed=True,
        )
        ctx = context_for_test(github=fake_github, cwd=tmp_path)

        entry = StackLandEntry(
            branch="A",
            pr_number=101,
            pr_details=pr_a,
            worktree_path=None,
            plan_id=None,
            objective_number=None,
        )
        _merge_and_cleanup_branch(ctx, tmp_path, entry)

        assert 101 in fake_github.merged_prs
        assert "A" in fake_github.deleted_remote_branches

    def test_fails_on_merge_error(self, tmp_path: Path) -> None:
        """Raises on merge failure."""
        pr_a = _make_pr_details(pr_number=101, branch="A")
        fake_github = FakeLocalGitHub(
            pr_details={101: pr_a},
            merge_should_succeed=False,
        )
        ctx = context_for_test(github=fake_github, cwd=tmp_path)

        entry = StackLandEntry(
            branch="A",
            pr_number=101,
            pr_details=pr_a,
            worktree_path=None,
            plan_id=None,
            objective_number=None,
        )
        with pytest.raises(UserFacingCliError):
            _merge_and_cleanup_branch(ctx, tmp_path, entry)


# ============================================================================
# _rebase_and_push
# ============================================================================


class TestRebaseAndPush:
    def test_fetches_rebases_and_pushes(self, tmp_path: Path) -> None:
        """Fetches trunk, rebases, and force-pushes."""
        fake_git = FakeGit(
            current_branches={tmp_path: "B"},
            rebase_onto_result=RebaseResult(success=True, conflict_files=()),
            worktrees={tmp_path: [WorktreeInfo(path=tmp_path, branch="B")]},
        )
        fake_graphite = FakeGraphite(stacks={"B": ["main", "A", "B"]})
        ctx = context_for_test(git=fake_git, graphite=fake_graphite, cwd=tmp_path)

        _rebase_and_push(ctx, tmp_path, "B", "main")

        assert ("origin", "main") in fake_git.fetched_branches
        assert len(fake_git.rebase_onto_calls) == 1
        assert fake_git.rebase_onto_calls[0] == (tmp_path, "origin/main")
        assert len(fake_git.pushed_branches) == 1

    def test_aborts_on_conflict(self, tmp_path: Path) -> None:
        """Aborts rebase and raises error on conflict."""
        fake_git = FakeGit(
            current_branches={tmp_path: "B"},
            rebase_onto_result=RebaseResult(success=False, conflict_files=("file.py",)),
            worktrees={tmp_path: [WorktreeInfo(path=tmp_path, branch="B")]},
        )
        ctx = context_for_test(git=fake_git, cwd=tmp_path)

        with pytest.raises(UserFacingCliError):
            _rebase_and_push(ctx, tmp_path, "B", "main")

        assert len(fake_git.rebase_abort_calls) == 1


# ============================================================================
# execute_land_stack (integration)
# ============================================================================


class TestExecuteLandStack:
    def test_happy_path_three_branch_stack(self, tmp_path: Path) -> None:
        """Lands 3-branch stack in order: A, B, C."""
        pr_a = _make_pr_details(pr_number=101, branch="A", base_ref_name="main")
        pr_b = _make_pr_details(pr_number=102, branch="B", base_ref_name="A")
        pr_c = _make_pr_details(pr_number=103, branch="C", base_ref_name="B")

        fake_graphite = FakeGraphite(stacks={"C": ["main", "A", "B", "C"]})

        fake_git = FakeGit(
            current_branches={tmp_path: "C"},
            default_branches={tmp_path: "main"},
            rebase_onto_result=RebaseResult(success=True, conflict_files=()),
            worktrees={tmp_path: [WorktreeInfo(path=tmp_path, branch="C")]},
            local_branches={tmp_path: ["main", "A", "B", "C"]},
            branch_divergence={
                (tmp_path, "main", "origin"): BranchDivergence(
                    is_diverged=False,
                    ahead=0,
                    behind=0,
                ),
            },
        )

        fake_github = FakeLocalGitHub(
            prs_by_branch={"A": pr_a, "B": pr_b, "C": pr_c},
            pr_details={101: pr_a, 102: pr_b, 103: pr_c},
            prs={
                "A": _make_pull_request_info(pr_number=101, branch="A"),
                "B": _make_pull_request_info(pr_number=102, branch="B"),
                "C": _make_pull_request_info(pr_number=103, branch="C"),
            },
            merge_should_succeed=True,
        )

        ctx = context_for_test(
            git=fake_git,
            github=fake_github,
            graphite=fake_graphite,
            cwd=tmp_path,
        )

        with pytest.raises(SystemExit) as exc_info:
            execute_land_stack(
                ctx,
                repo=_make_repo(tmp_path),
                force=True,
                pull_flag=True,
                no_delete=False,
                skip_learn=True,
            )
        assert exc_info.value.code == 0

        # All 3 PRs merged
        assert 101 in fake_github.merged_prs
        assert 102 in fake_github.merged_prs
        assert 103 in fake_github.merged_prs

        # Remote branches deleted
        assert "A" in fake_github.deleted_remote_branches
        assert "B" in fake_github.deleted_remote_branches
        assert "C" in fake_github.deleted_remote_branches

        # PR bases were re-parented before merges
        assert (102, "main") in fake_github.updated_pr_bases
        assert (103, "main") in fake_github.updated_pr_bases

        # Rebases happened for B and C (not A since it's first)
        assert len(fake_git.rebase_onto_calls) == 2

    def test_single_branch_stack(self, tmp_path: Path) -> None:
        """Single-branch stack works (no rebase needed)."""
        pr_a = _make_pr_details(pr_number=101, branch="A", base_ref_name="main")
        fake_graphite = FakeGraphite(stacks={"A": ["main", "A"]})

        fake_git = FakeGit(
            current_branches={tmp_path: "A"},
            default_branches={tmp_path: "main"},
            worktrees={tmp_path: [WorktreeInfo(path=tmp_path, branch="A")]},
            local_branches={tmp_path: ["main", "A"]},
            branch_divergence={
                (tmp_path, "main", "origin"): BranchDivergence(
                    is_diverged=False,
                    ahead=0,
                    behind=0,
                ),
            },
        )

        fake_github = FakeLocalGitHub(
            prs_by_branch={"A": pr_a},
            pr_details={101: pr_a},
            prs={"A": _make_pull_request_info(pr_number=101, branch="A")},
            merge_should_succeed=True,
        )

        ctx = context_for_test(
            git=fake_git,
            github=fake_github,
            graphite=fake_graphite,
            cwd=tmp_path,
        )

        with pytest.raises(SystemExit) as exc_info:
            execute_land_stack(
                ctx,
                repo=_make_repo(tmp_path),
                force=True,
                pull_flag=True,
                no_delete=False,
                skip_learn=True,
            )
        assert exc_info.value.code == 0

        assert 101 in fake_github.merged_prs
        assert len(fake_git.rebase_onto_calls) == 0

    def test_rebase_conflict_bails_cleanly(self, tmp_path: Path) -> None:
        """Rebase conflict aborts cleanly after first PR merged."""
        pr_a = _make_pr_details(pr_number=101, branch="A", base_ref_name="main")
        pr_b = _make_pr_details(pr_number=102, branch="B", base_ref_name="A")

        fake_graphite = FakeGraphite(stacks={"B": ["main", "A", "B"]})

        fake_git = FakeGit(
            current_branches={tmp_path: "B"},
            default_branches={tmp_path: "main"},
            rebase_onto_result=RebaseResult(success=False, conflict_files=("file.py",)),
            worktrees={tmp_path: [WorktreeInfo(path=tmp_path, branch="B")]},
        )

        fake_github = FakeLocalGitHub(
            prs_by_branch={"A": pr_a, "B": pr_b},
            pr_details={101: pr_a, 102: pr_b},
            prs={
                "A": _make_pull_request_info(pr_number=101, branch="A"),
                "B": _make_pull_request_info(pr_number=102, branch="B"),
            },
            merge_should_succeed=True,
        )

        ctx = context_for_test(
            git=fake_git,
            github=fake_github,
            graphite=fake_graphite,
            cwd=tmp_path,
        )

        with pytest.raises(UserFacingCliError):
            execute_land_stack(
                ctx,
                repo=_make_repo(tmp_path),
                force=True,
                pull_flag=True,
                no_delete=False,
                skip_learn=True,
            )

        # First PR was merged (before rebase of B)
        assert 101 in fake_github.merged_prs
        # Second PR was not merged (rebase conflict)
        assert 102 not in fake_github.merged_prs

    def test_merge_failure(self, tmp_path: Path) -> None:
        """Merge failure stops the stack."""
        pr_a = _make_pr_details(pr_number=101, branch="A", base_ref_name="main")
        fake_graphite = FakeGraphite(stacks={"A": ["main", "A"]})

        fake_git = FakeGit(
            current_branches={tmp_path: "A"},
            default_branches={tmp_path: "main"},
            worktrees={tmp_path: [WorktreeInfo(path=tmp_path, branch="A")]},
        )

        fake_github = FakeLocalGitHub(
            prs_by_branch={"A": pr_a},
            pr_details={101: pr_a},
            prs={"A": _make_pull_request_info(pr_number=101, branch="A")},
            merge_should_succeed=False,
        )

        ctx = context_for_test(
            git=fake_git,
            github=fake_github,
            graphite=fake_graphite,
            cwd=tmp_path,
        )

        with pytest.raises(UserFacingCliError):
            execute_land_stack(
                ctx,
                repo=_make_repo(tmp_path),
                force=True,
                pull_flag=True,
                no_delete=False,
                skip_learn=True,
            )

    def test_no_delete_preserves_branches(self, tmp_path: Path) -> None:
        """With no_delete=True, local branches are preserved."""
        pr_a = _make_pr_details(pr_number=101, branch="A", base_ref_name="main")
        fake_graphite = FakeGraphite(stacks={"A": ["main", "A"]})

        fake_git = FakeGit(
            current_branches={tmp_path: "A"},
            default_branches={tmp_path: "main"},
            worktrees={tmp_path: [WorktreeInfo(path=tmp_path, branch="A")]},
            branch_divergence={
                (tmp_path, "main", "origin"): BranchDivergence(
                    is_diverged=False,
                    ahead=0,
                    behind=0,
                ),
            },
        )

        fake_github = FakeLocalGitHub(
            prs_by_branch={"A": pr_a},
            pr_details={101: pr_a},
            prs={"A": _make_pull_request_info(pr_number=101, branch="A")},
            merge_should_succeed=True,
        )

        ctx = context_for_test(
            git=fake_git,
            github=fake_github,
            graphite=fake_graphite,
            cwd=tmp_path,
        )

        with pytest.raises(SystemExit) as exc_info:
            execute_land_stack(
                ctx,
                repo=_make_repo(tmp_path),
                force=True,
                pull_flag=True,
                no_delete=True,
                skip_learn=True,
            )
        assert exc_info.value.code == 0

        # PR merged
        assert 101 in fake_github.merged_prs
        # No local branch deletions
        assert len(fake_git.deleted_branches) == 0
