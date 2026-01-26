"""Unit tests for land target resolver functions."""

from pathlib import Path

import pytest

from erk.cli.commands.land_cmd import (
    _resolve_land_target_branch,
    _resolve_land_target_current_branch,
    _resolve_land_target_pr,
)
from erk.core.context import context_for_test
from erk_shared.context.types import RepoContext
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails


def create_test_pr_details(
    *,
    pr_number: int,
    branch: str,
    state: str,
    base_ref_name: str,
    is_cross_repository: bool = False,
) -> PRDetails:
    """Create PRDetails for testing."""
    return PRDetails(
        number=pr_number,
        url=f"https://github.com/owner/repo/pull/{pr_number}",
        title="Test PR",
        body="Test body",
        state=state,
        base_ref_name=base_ref_name,
        head_ref_name=branch,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        is_draft=False,
        is_cross_repository=is_cross_repository,
        owner="owner",
        repo="repo",
    )


def create_test_repo_context(tmp_path: Path) -> RepoContext:
    """Create RepoContext for testing."""
    return RepoContext(
        root=tmp_path,
        repo_name="test-repo",
        repo_dir=tmp_path / ".erk" / "repos" / "test-repo",
        worktrees_dir=tmp_path / ".erk" / "repos" / "test-repo" / "worktrees",
        pool_json_path=tmp_path / ".erk" / "repos" / "test-repo" / "pool.json",
        main_repo_root=tmp_path,
    )


class TestResolveCurrentBranch:
    """Tests for _resolve_land_target_current_branch."""

    def test_resolves_current_branch_without_graphite(self, tmp_path: Path) -> None:
        """Test resolving current branch when Graphite is disabled."""
        repo_root = tmp_path
        branch = "feature-branch"
        pr_number = 123

        pr_details = create_test_pr_details(
            pr_number=pr_number,
            branch=branch,
            state="OPEN",
            base_ref_name="main",
        )

        worktree_info = WorktreeInfo(
            path=repo_root,
            branch=branch,
            is_root=True,
        )

        fake_git = FakeGit(
            current_branches={repo_root: branch},
            worktrees={repo_root: [worktree_info]},
            default_branches={repo_root: "main"},
        )
        fake_github = FakeGitHub(prs_by_branch={branch: pr_details})

        ctx = context_for_test(
            git=fake_git,
            github=fake_github,
            graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
            cwd=repo_root,
        )

        repo = create_test_repo_context(tmp_path)

        target = _resolve_land_target_current_branch(ctx, repo=repo, up_flag=False)

        assert target.branch == branch
        assert target.pr_details.number == pr_number
        assert target.worktree_path == repo_root
        assert target.is_current_branch is True
        assert target.use_graphite is False
        assert target.target_child_branch is None

    def test_fails_if_not_on_branch(self, tmp_path: Path) -> None:
        """Test that resolver fails when in detached HEAD state."""
        repo_root = tmp_path

        fake_git = FakeGit(
            current_branches={repo_root: None},  # Detached HEAD
            default_branches={repo_root: "main"},
        )

        ctx = context_for_test(
            git=fake_git,
            graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
            cwd=repo_root,
        )

        repo = create_test_repo_context(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            _resolve_land_target_current_branch(ctx, repo=repo, up_flag=False)

        assert exc_info.value.code == 1

    def test_fails_if_no_pr_for_branch(self, tmp_path: Path) -> None:
        """Test that resolver fails when no PR exists for branch."""
        repo_root = tmp_path
        branch = "feature-branch"

        worktree_info = WorktreeInfo(
            path=repo_root,
            branch=branch,
            is_root=True,
        )

        fake_git = FakeGit(
            current_branches={repo_root: branch},
            worktrees={repo_root: [worktree_info]},
            default_branches={repo_root: "main"},
        )
        # No PR configured in FakeGitHub
        fake_github = FakeGitHub()

        ctx = context_for_test(
            git=fake_git,
            github=fake_github,
            graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
            cwd=repo_root,
        )

        repo = create_test_repo_context(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            _resolve_land_target_current_branch(ctx, repo=repo, up_flag=False)

        assert exc_info.value.code == 1


class TestResolvePr:
    """Tests for _resolve_land_target_pr."""

    def test_resolves_pr_by_number(self, tmp_path: Path) -> None:
        """Test resolving a PR by number."""
        repo_root = tmp_path
        branch = "feature-branch"
        pr_number = 123

        pr_details = create_test_pr_details(
            pr_number=pr_number,
            branch=branch,
            state="OPEN",
            base_ref_name="main",
        )

        fake_git = FakeGit(
            current_branches={repo_root: "other-branch"},
            default_branches={repo_root: "main"},
        )
        fake_github = FakeGitHub(pr_details={pr_number: pr_details})

        ctx = context_for_test(
            git=fake_git,
            github=fake_github,
            graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
            cwd=repo_root,
        )

        repo = create_test_repo_context(tmp_path)

        target = _resolve_land_target_pr(ctx, repo=repo, pr_number=pr_number, up_flag=False)

        assert target.branch == branch
        assert target.pr_details.number == pr_number
        assert target.worktree_path is None  # No worktree for this branch
        assert target.is_current_branch is False
        assert target.use_graphite is False
        assert target.target_child_branch is None

    def test_handles_fork_pr(self, tmp_path: Path) -> None:
        """Test that fork PRs use pr/<number> branch naming."""
        repo_root = tmp_path
        fork_branch = "contributor-branch"
        pr_number = 456

        pr_details = create_test_pr_details(
            pr_number=pr_number,
            branch=fork_branch,
            state="OPEN",
            base_ref_name="main",
            is_cross_repository=True,
        )

        fake_git = FakeGit(
            current_branches={repo_root: "main"},
            default_branches={repo_root: "main"},
        )
        fake_github = FakeGitHub(pr_details={pr_number: pr_details})

        ctx = context_for_test(
            git=fake_git,
            github=fake_github,
            graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
            cwd=repo_root,
        )

        repo = create_test_repo_context(tmp_path)

        target = _resolve_land_target_pr(ctx, repo=repo, pr_number=pr_number, up_flag=False)

        # Fork PRs use pr/<number> naming convention
        assert target.branch == f"pr/{pr_number}"
        assert target.pr_details.number == pr_number

    def test_rejects_up_flag(self, tmp_path: Path) -> None:
        """Test that --up flag is rejected for PR landing."""
        repo_root = tmp_path
        pr_number = 123

        pr_details = create_test_pr_details(
            pr_number=pr_number,
            branch="feature-branch",
            state="OPEN",
            base_ref_name="main",
        )

        fake_git = FakeGit(default_branches={repo_root: "main"})
        fake_github = FakeGitHub(pr_details={pr_number: pr_details})

        ctx = context_for_test(
            git=fake_git,
            github=fake_github,
            graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
            cwd=repo_root,
        )

        repo = create_test_repo_context(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            _resolve_land_target_pr(ctx, repo=repo, pr_number=pr_number, up_flag=True)

        assert exc_info.value.code == 1

    def test_fails_if_pr_not_found(self, tmp_path: Path) -> None:
        """Test that resolver fails when PR doesn't exist."""
        repo_root = tmp_path
        pr_number = 999

        fake_git = FakeGit(default_branches={repo_root: "main"})
        fake_github = FakeGitHub()  # No PRs

        ctx = context_for_test(
            git=fake_git,
            github=fake_github,
            graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
            cwd=repo_root,
        )

        repo = create_test_repo_context(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            _resolve_land_target_pr(ctx, repo=repo, pr_number=pr_number, up_flag=False)

        assert exc_info.value.code == 1


class TestResolveBranch:
    """Tests for _resolve_land_target_branch."""

    def test_resolves_branch_by_name(self, tmp_path: Path) -> None:
        """Test resolving a PR by branch name."""
        repo_root = tmp_path
        branch = "feature-branch"
        pr_number = 123

        pr_details = create_test_pr_details(
            pr_number=pr_number,
            branch=branch,
            state="OPEN",
            base_ref_name="main",
        )

        fake_git = FakeGit(
            current_branches={repo_root: "other-branch"},
            default_branches={repo_root: "main"},
        )
        fake_github = FakeGitHub(prs_by_branch={branch: pr_details})

        ctx = context_for_test(
            git=fake_git,
            github=fake_github,
            graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
            cwd=repo_root,
        )

        repo = create_test_repo_context(tmp_path)

        target = _resolve_land_target_branch(ctx, repo=repo, branch_name=branch)

        assert target.branch == branch
        assert target.pr_details.number == pr_number
        assert target.worktree_path is None
        assert target.is_current_branch is False
        assert target.use_graphite is False
        assert target.target_child_branch is None

    def test_detects_when_in_target_worktree(self, tmp_path: Path) -> None:
        """Test that is_current_branch is set when in target branch's worktree."""
        repo_root = tmp_path
        branch = "feature-branch"
        pr_number = 123

        pr_details = create_test_pr_details(
            pr_number=pr_number,
            branch=branch,
            state="OPEN",
            base_ref_name="main",
        )

        worktree_info = WorktreeInfo(
            path=repo_root,
            branch=branch,
            is_root=True,
        )

        fake_git = FakeGit(
            current_branches={repo_root: branch},  # On the target branch
            worktrees={repo_root: [worktree_info]},
            default_branches={repo_root: "main"},
        )
        fake_github = FakeGitHub(prs_by_branch={branch: pr_details})

        ctx = context_for_test(
            git=fake_git,
            github=fake_github,
            graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
            cwd=repo_root,
        )

        repo = create_test_repo_context(tmp_path)

        target = _resolve_land_target_branch(ctx, repo=repo, branch_name=branch)

        assert target.branch == branch
        assert target.is_current_branch is True
        assert target.worktree_path == repo_root

    def test_fails_if_no_pr_for_branch(self, tmp_path: Path) -> None:
        """Test that resolver fails when no PR exists for branch."""
        repo_root = tmp_path
        branch = "feature-branch"

        fake_git = FakeGit(
            current_branches={repo_root: "main"},
            default_branches={repo_root: "main"},
        )
        fake_github = FakeGitHub()  # No PRs

        ctx = context_for_test(
            git=fake_git,
            github=fake_github,
            graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
            cwd=repo_root,
        )

        repo = create_test_repo_context(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            _resolve_land_target_branch(ctx, repo=repo, branch_name=branch)

        assert exc_info.value.code == 1
