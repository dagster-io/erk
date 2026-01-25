"""Unit tests for _validate_pr_for_landing shared validation function."""

from pathlib import Path

import pytest

from erk.cli.commands.land_cmd import LandTarget, _validate_pr_for_landing
from erk.core.context import context_for_test
from erk_shared.context.types import RepoContext
from erk_shared.gateway.console.fake import FakeConsole
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails


def create_test_pr_details(
    *,
    pr_number: int,
    branch: str,
    state: str,
    base_ref_name: str,
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
        is_cross_repository=False,
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


class TestValidatePrForLandingPrState:
    """Tests for PR state validation in _validate_pr_for_landing."""

    def test_fails_if_pr_not_open(self, tmp_path: Path) -> None:
        """Test that _validate_pr_for_landing fails if PR is not open."""
        repo_root = tmp_path
        branch = "feature-branch"
        pr_number = 123

        pr_details = create_test_pr_details(
            pr_number=pr_number,
            branch=branch,
            state="MERGED",
            base_ref_name="main",
        )

        target = LandTarget(
            branch=branch,
            pr_details=pr_details,
            worktree_path=tmp_path / "wt",
            is_current_branch=False,
            use_graphite=False,
            target_child_branch=None,
        )

        fake_git = FakeGit(default_branches={repo_root: "main"})
        ctx = context_for_test(
            git=fake_git,
            graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
            cwd=repo_root,
        )

        repo = create_test_repo_context(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            _validate_pr_for_landing(ctx, repo=repo, target=target, force=False, script=False)

        assert exc_info.value.code == 1

    def test_fails_if_pr_closed(self, tmp_path: Path) -> None:
        """Test that _validate_pr_for_landing fails if PR is closed."""
        repo_root = tmp_path
        branch = "feature-branch"
        pr_number = 123

        pr_details = create_test_pr_details(
            pr_number=pr_number,
            branch=branch,
            state="CLOSED",
            base_ref_name="main",
        )

        target = LandTarget(
            branch=branch,
            pr_details=pr_details,
            worktree_path=tmp_path / "wt",
            is_current_branch=False,
            use_graphite=False,
            target_child_branch=None,
        )

        fake_git = FakeGit(default_branches={repo_root: "main"})
        ctx = context_for_test(
            git=fake_git,
            graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
            cwd=repo_root,
        )

        repo = create_test_repo_context(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            _validate_pr_for_landing(ctx, repo=repo, target=target, force=False, script=False)

        assert exc_info.value.code == 1


class TestValidatePrForLandingBaseRef:
    """Tests for PR base branch validation in _validate_pr_for_landing."""

    def test_fails_if_pr_not_targeting_trunk_non_graphite(self, tmp_path: Path) -> None:
        """Test that _validate_pr_for_landing fails if PR base is not trunk in non-Graphite mode."""
        repo_root = tmp_path
        branch = "feature-branch"
        pr_number = 123

        pr_details = create_test_pr_details(
            pr_number=pr_number,
            branch=branch,
            state="OPEN",
            base_ref_name="some-other-branch",
        )

        target = LandTarget(
            branch=branch,
            pr_details=pr_details,
            worktree_path=tmp_path / "wt",
            is_current_branch=False,
            use_graphite=False,
            target_child_branch=None,
        )

        fake_git = FakeGit(default_branches={repo_root: "main"})
        ctx = context_for_test(
            git=fake_git,
            graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
            cwd=repo_root,
        )

        repo = create_test_repo_context(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            _validate_pr_for_landing(ctx, repo=repo, target=target, force=False, script=False)

        assert exc_info.value.code == 1

    def test_skips_base_check_for_graphite_mode(self, tmp_path: Path) -> None:
        """Test that base-is-trunk check is skipped when use_graphite=True.

        Graphite validates the stack structure differently, so we trust it.
        """
        repo_root = tmp_path
        branch = "feature-branch"
        pr_number = 123

        # PR targeting non-trunk - would fail non-Graphite validation
        pr_details = create_test_pr_details(
            pr_number=pr_number,
            branch=branch,
            state="OPEN",
            base_ref_name="parent-branch",
        )

        target = LandTarget(
            branch=branch,
            pr_details=pr_details,
            worktree_path=tmp_path / "wt",
            is_current_branch=False,
            use_graphite=True,  # Graphite mode - base check skipped
            target_child_branch=None,
        )

        fake_git = FakeGit(default_branches={repo_root: "main"})
        fake_github = FakeGitHub()
        # FakeConsole with confirm_responses for cleanup confirmation prompt
        fake_console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=True,
            is_stderr_tty=True,
            confirm_responses=[True],
        )
        ctx = context_for_test(
            git=fake_git,
            github=fake_github,
            graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
            console=fake_console,
            cwd=repo_root,
        )

        repo = create_test_repo_context(tmp_path)

        # Should not raise - base check skipped for Graphite
        _validate_pr_for_landing(ctx, repo=repo, target=target, force=False, script=False)


class TestValidatePrForLandingCleanWorkingTree:
    """Tests for clean working tree check in _validate_pr_for_landing."""

    def test_fails_if_current_branch_has_uncommitted_changes(self, tmp_path: Path) -> None:
        """Test that _validate_pr_for_landing fails if current branch has uncommitted changes."""
        repo_root = tmp_path
        branch = "feature-branch"
        pr_number = 123

        pr_details = create_test_pr_details(
            pr_number=pr_number,
            branch=branch,
            state="OPEN",
            base_ref_name="main",
        )

        target = LandTarget(
            branch=branch,
            pr_details=pr_details,
            worktree_path=repo_root,
            is_current_branch=True,  # Current branch
            use_graphite=False,
            target_child_branch=None,
        )

        # Simulate uncommitted changes
        fake_git = FakeGit(
            default_branches={repo_root: "main"},
            file_statuses={repo_root: ([], ["modified.py"], [])},
        )
        ctx = context_for_test(
            git=fake_git,
            graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
            cwd=repo_root,
        )

        repo = create_test_repo_context(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            _validate_pr_for_landing(ctx, repo=repo, target=target, force=False, script=False)

        assert exc_info.value.code == 1

    def test_skips_clean_check_for_non_current_branch(self, tmp_path: Path) -> None:
        """Test that clean working tree check is skipped when not current branch."""
        repo_root = tmp_path
        branch = "feature-branch"
        pr_number = 123

        pr_details = create_test_pr_details(
            pr_number=pr_number,
            branch=branch,
            state="OPEN",
            base_ref_name="main",
        )

        target = LandTarget(
            branch=branch,
            pr_details=pr_details,
            worktree_path=repo_root,
            is_current_branch=False,  # Not current branch
            use_graphite=False,
            target_child_branch=None,
        )

        # Simulate uncommitted changes - should be ignored since not current branch
        fake_git = FakeGit(
            default_branches={repo_root: "main"},
            file_statuses={repo_root: ([], ["modified.py"], [])},
        )
        fake_github = FakeGitHub()
        # FakeConsole with confirm_responses for cleanup confirmation prompt
        fake_console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=True,
            is_stderr_tty=True,
            confirm_responses=[True],
        )
        ctx = context_for_test(
            git=fake_git,
            github=fake_github,
            graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
            console=fake_console,
            cwd=repo_root,
        )

        repo = create_test_repo_context(tmp_path)

        # Should not raise - clean check skipped for non-current branches
        _validate_pr_for_landing(ctx, repo=repo, target=target, force=False, script=False)


class TestValidatePrForLandingSuccess:
    """Tests for successful validation paths."""

    def test_succeeds_for_valid_pr(self, tmp_path: Path) -> None:
        """Test that _validate_pr_for_landing succeeds for a valid PR."""
        repo_root = tmp_path
        branch = "feature-branch"
        pr_number = 123

        pr_details = create_test_pr_details(
            pr_number=pr_number,
            branch=branch,
            state="OPEN",
            base_ref_name="main",
        )

        target = LandTarget(
            branch=branch,
            pr_details=pr_details,
            worktree_path=tmp_path / "wt",
            is_current_branch=False,
            use_graphite=False,
            target_child_branch=None,
        )

        fake_git = FakeGit(default_branches={repo_root: "main"})
        fake_github = FakeGitHub()
        # FakeConsole with confirm_responses for cleanup confirmation prompt
        fake_console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=True,
            is_stderr_tty=True,
            confirm_responses=[True],
        )
        ctx = context_for_test(
            git=fake_git,
            github=fake_github,
            graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
            console=fake_console,
            cwd=repo_root,
        )

        repo = create_test_repo_context(tmp_path)

        # Should not raise
        _validate_pr_for_landing(ctx, repo=repo, target=target, force=False, script=False)
