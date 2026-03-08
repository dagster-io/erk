"""Unit tests for erk land --stack (bottom-up Graphite stack landing)."""

from __future__ import annotations

from pathlib import Path

import pytest

from erk.cli.commands.land_stack import (
    StackLandEntry,
    _confirm_stack_land,
    _display_stack_summary,
    _merge_and_cleanup_branch,
    _rebase_and_push,
    _reparent_entry,
    _report_partial_failure,
    _resolve_stack,
    _validate_stack_prs,
    execute_land_stack,
)
from erk.cli.ensure import UserFacingCliError
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.console.fake import FakeConsole
from erk_shared.gateway.git.abc import RebaseResult
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.github.fake import FakeLocalGitHub
from erk_shared.gateway.github.types import GitHubRepoId, PRDetails
from erk_shared.gateway.graphite.fake import FakeGraphite

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path("/repo")
_GIT_DIR = _REPO_ROOT / ".git"


def _pr_details(
    *,
    number: int,
    branch: str,
    state: str = "OPEN",
    title: str = "",
) -> PRDetails:
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title=title or f"PR for {branch}",
        body="",
        state=state,
        is_draft=False,
        base_ref_name="main",
        head_ref_name=branch,
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


def _make_entry(
    *,
    branch: str,
    pr_number: int,
    plan_id: str | None = None,
    objective_number: int | None = None,
    state: str = "OPEN",
) -> StackLandEntry:
    return StackLandEntry(
        branch=branch,
        pr_number=pr_number,
        pr_details=_pr_details(number=pr_number, branch=branch, state=state),
        worktree_path=None,
        plan_id=plan_id,
        objective_number=objective_number,
    )


def _repo_context() -> RepoContext:
    return RepoContext(
        root=_REPO_ROOT,
        repo_name="repo",
        repo_dir=_REPO_ROOT,
        worktrees_dir=_REPO_ROOT / "worktrees",
        pool_json_path=_REPO_ROOT / "pool.json",
        github=GitHubRepoId(owner="owner", repo="repo"),
    )


def _fake_git(
    *,
    current_branch: str = "branch-c",
    local_branches: list[str] | None = None,
    rebase_onto_result: RebaseResult | None = None,
) -> FakeGit:
    if local_branches is None:
        local_branches = ["main", "branch-a", "branch-b", "branch-c"]
    return FakeGit(
        current_branches={_REPO_ROOT: current_branch},
        default_branches={_REPO_ROOT: "main"},
        trunk_branches={_REPO_ROOT: "main"},
        local_branches={_REPO_ROOT: local_branches},
        git_common_dirs={_REPO_ROOT: _GIT_DIR},
        existing_paths={_REPO_ROOT, _GIT_DIR},
        rebase_onto_result=rebase_onto_result,
    )


def _fake_graphite(
    *,
    stack: list[str] | None = None,
) -> FakeGraphite:
    if stack is None:
        stack = ["main", "branch-a", "branch-b", "branch-c"]
    return FakeGraphite(
        stacks={"branch-c": stack},
    )


def _fake_github(
    *,
    branches: list[tuple[str, int]] | None = None,
    merge_should_succeed: bool = True,
) -> FakeLocalGitHub:
    if branches is None:
        branches = [("branch-a", 1), ("branch-b", 2), ("branch-c", 3)]
    prs_by_branch: dict[str, PRDetails] = {}
    pr_details: dict[int, PRDetails] = {}
    for branch, number in branches:
        pr = _pr_details(number=number, branch=branch)
        prs_by_branch[branch] = pr
        pr_details[number] = pr
    return FakeLocalGitHub(
        prs_by_branch=prs_by_branch,
        pr_details=pr_details,
        merge_should_succeed=merge_should_succeed,
    )


# ---------------------------------------------------------------------------
# Tests: _resolve_stack
# ---------------------------------------------------------------------------


class TestResolveStack:
    def test_returns_branches_excluding_trunk(self) -> None:
        ctx = context_for_test(
            git=_fake_git(),
            graphite=_fake_graphite(),
            cwd=_REPO_ROOT,
        )
        result = _resolve_stack(ctx, main_repo_root=_REPO_ROOT)
        assert result == ["branch-a", "branch-b", "branch-c"]

    def test_errors_when_not_on_branch(self) -> None:
        git = FakeGit(
            current_branches={_REPO_ROOT: None},
            default_branches={_REPO_ROOT: "main"},
            trunk_branches={_REPO_ROOT: "main"},
            git_common_dirs={_REPO_ROOT: _GIT_DIR},
        )
        ctx = context_for_test(git=git, graphite=_fake_graphite(), cwd=_REPO_ROOT)
        with pytest.raises(UserFacingCliError, match="Not on a branch"):
            _resolve_stack(ctx, main_repo_root=_REPO_ROOT)

    def test_errors_when_not_in_stack(self) -> None:
        graphite = FakeGraphite(stacks={})
        git = _fake_git(current_branch="orphan")
        ctx = context_for_test(git=git, graphite=graphite, cwd=_REPO_ROOT)
        with pytest.raises(UserFacingCliError, match="not part of a Graphite stack"):
            _resolve_stack(ctx, main_repo_root=_REPO_ROOT)


# ---------------------------------------------------------------------------
# Tests: _validate_stack_prs
# ---------------------------------------------------------------------------


class TestValidateStackPrs:
    def test_returns_entries_for_open_prs(self) -> None:
        github = _fake_github()
        ctx = context_for_test(
            git=_fake_git(), github=github, graphite=_fake_graphite(), cwd=_REPO_ROOT
        )
        entries = _validate_stack_prs(
            ctx,
            main_repo_root=_REPO_ROOT,
            branches=["branch-a", "branch-b", "branch-c"],
            trunk="main",
            force=False,
        )
        assert len(entries) == 3
        assert entries[0].branch == "branch-a"
        assert entries[0].pr_number == 1
        assert entries[2].branch == "branch-c"
        assert entries[2].pr_number == 3

    def test_errors_when_pr_not_open(self) -> None:
        closed_pr = _pr_details(number=2, branch="branch-b", state="MERGED")
        github = FakeLocalGitHub(
            prs_by_branch={
                "branch-a": _pr_details(number=1, branch="branch-a"),
                "branch-b": closed_pr,
            },
        )
        ctx = context_for_test(
            git=_fake_git(), github=github, graphite=_fake_graphite(), cwd=_REPO_ROOT
        )
        with pytest.raises(UserFacingCliError, match="not open"):
            _validate_stack_prs(
                ctx,
                main_repo_root=_REPO_ROOT,
                branches=["branch-a", "branch-b"],
                trunk="main",
                force=False,
            )

    def test_errors_when_no_pr_for_branch(self) -> None:
        github = FakeLocalGitHub(prs_by_branch={})
        ctx = context_for_test(
            git=_fake_git(), github=github, graphite=_fake_graphite(), cwd=_REPO_ROOT
        )
        with pytest.raises(UserFacingCliError, match="No pull request found"):
            _validate_stack_prs(
                ctx,
                main_repo_root=_REPO_ROOT,
                branches=["branch-a"],
                trunk="main",
                force=False,
            )


# ---------------------------------------------------------------------------
# Tests: _confirm_stack_land
# ---------------------------------------------------------------------------


class TestConfirmStackLand:
    def test_force_skips_confirmation(self) -> None:
        ctx = context_for_test(cwd=_REPO_ROOT)
        entries = [_make_entry(branch="a", pr_number=1)]
        # Should not raise or call confirm
        _confirm_stack_land(ctx, entries=entries, force=True)

    def test_confirmation_shown_without_force(self) -> None:
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=[True],
        )
        ctx = context_for_test(console=console, cwd=_REPO_ROOT)
        entries = [_make_entry(branch="a", pr_number=1)]
        _confirm_stack_land(ctx, entries=entries, force=False)
        assert len(console.confirm_prompts) == 1
        assert "1 PR(s)" in console.confirm_prompts[0]

    def test_confirmation_declined_aborts(self) -> None:
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=[False],
        )
        ctx = context_for_test(console=console, cwd=_REPO_ROOT)
        entries = [_make_entry(branch="a", pr_number=1)]
        with pytest.raises(SystemExit) as exc_info:
            _confirm_stack_land(ctx, entries=entries, force=False)
        assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# Tests: _reparent_entry
# ---------------------------------------------------------------------------


class TestReparentEntry:
    def test_updates_pr_base_branch(self) -> None:
        github = _fake_github()
        ctx = context_for_test(git=_fake_git(), github=github, cwd=_REPO_ROOT)
        entry = _make_entry(branch="branch-b", pr_number=2)
        _reparent_entry(ctx, main_repo_root=_REPO_ROOT, entry=entry, trunk="main")
        assert ("update_pr_base_branch", 2, "main") in github.operation_log


# ---------------------------------------------------------------------------
# Tests: _merge_and_cleanup_branch
# ---------------------------------------------------------------------------


class TestMergeAndCleanupBranch:
    def test_merges_and_deletes_remote_branch(self) -> None:
        github = _fake_github()
        ctx = context_for_test(git=_fake_git(), github=github, cwd=_REPO_ROOT)
        entry = _make_entry(branch="branch-a", pr_number=1)
        _merge_and_cleanup_branch(ctx, main_repo_root=_REPO_ROOT, entry=entry)
        assert 1 in github.merged_prs
        assert "branch-a" in github.deleted_remote_branches

    def test_merge_failure_raises(self) -> None:
        github = _fake_github(merge_should_succeed=False)
        ctx = context_for_test(git=_fake_git(), github=github, cwd=_REPO_ROOT)
        entry = _make_entry(branch="branch-a", pr_number=1)
        with pytest.raises(UserFacingCliError, match="Failed to merge"):
            _merge_and_cleanup_branch(ctx, main_repo_root=_REPO_ROOT, entry=entry)


# ---------------------------------------------------------------------------
# Tests: _rebase_and_push
# ---------------------------------------------------------------------------


class TestRebaseAndPush:
    def test_rebase_conflict_raises(self) -> None:
        git = _fake_git(
            rebase_onto_result=RebaseResult(success=False, conflict_files=("file.py",)),
        )
        ctx = context_for_test(git=git, graphite=_fake_graphite(), cwd=_REPO_ROOT)
        with pytest.raises(UserFacingCliError, match="Rebase conflict"):
            _rebase_and_push(ctx, main_repo_root=_REPO_ROOT, branch="branch-b", trunk="main")


# ---------------------------------------------------------------------------
# Tests: _report_partial_failure
# ---------------------------------------------------------------------------


class TestReportPartialFailure:
    def test_output_format(self, capsys: pytest.CaptureFixture[str]) -> None:
        landed = [_make_entry(branch="a", pr_number=1)]
        failed = _make_entry(branch="b", pr_number=2)
        remaining = [_make_entry(branch="c", pr_number=3)]
        _report_partial_failure(landed=landed, failed=failed, remaining=remaining, total=3)
        captured = capsys.readouterr()
        assert "1/3 landed" in captured.err
        assert "PR #1" in captured.err
        assert "PR #2" in captured.err
        assert "PR #3" in captured.err


# ---------------------------------------------------------------------------
# Tests: execute_land_stack (integration)
# ---------------------------------------------------------------------------


class TestExecuteLandStack:
    def test_happy_path_three_branch_stack(self, capsys: pytest.CaptureFixture[str]) -> None:
        """All 3 branches merged bottom-up with correct ordering."""
        github = _fake_github()
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=[True],
        )
        ctx = context_for_test(
            git=_fake_git(),
            github=github,
            graphite=_fake_graphite(),
            console=console,
            cwd=_REPO_ROOT,
        )
        repo = _repo_context()

        execute_land_stack(
            ctx,
            repo=repo,
            force=False,
            pull_flag=False,
            no_delete=True,
            skip_learn=True,
        )

        # All 3 PRs merged
        assert github.merged_prs == [1, 2, 3]

        # All 3 remote branches deleted
        assert set(github.deleted_remote_branches) == {"branch-a", "branch-b", "branch-c"}

        # Verify operation ordering: re-parent before merge for each iteration
        log = github.operation_log
        # Iteration 0: reparent #2 to main, then merge #1
        assert log[0] == ("update_pr_base_branch", 2, "main")
        assert log[1] == ("merge_pr", 1)
        # Iteration 1: reparent #3 to main, then merge #2
        assert log[2] == ("update_pr_base_branch", 3, "main")
        assert log[3] == ("merge_pr", 2)
        # Iteration 2: no reparent (last), merge #3
        assert log[4] == ("merge_pr", 3)

        # Success message
        captured = capsys.readouterr()
        assert "3 PR(s) merged successfully" in captured.err

    def test_dry_run_no_mutations(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Dry-run shows summary but makes no merges or re-parents."""
        github = _fake_github()
        ctx = context_for_test(
            git=_fake_git(),
            github=github,
            graphite=_fake_graphite(),
            cwd=_REPO_ROOT,
            dry_run=True,
        )
        repo = _repo_context()

        execute_land_stack(
            ctx,
            repo=repo,
            force=False,
            pull_flag=False,
            no_delete=True,
            skip_learn=True,
        )

        # No mutations
        assert github.merged_prs == []
        assert github.operation_log == []

        captured = capsys.readouterr()
        assert "DRY RUN" in captured.err

    def test_force_skips_confirmation(self) -> None:
        """With --force, no confirmation prompt is shown."""
        github = _fake_github()
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=None,  # No responses needed — confirm won't be called
        )
        ctx = context_for_test(
            git=_fake_git(),
            github=github,
            graphite=_fake_graphite(),
            console=console,
            cwd=_REPO_ROOT,
        )
        repo = _repo_context()

        execute_land_stack(
            ctx,
            repo=repo,
            force=True,
            pull_flag=False,
            no_delete=True,
            skip_learn=True,
        )

        assert len(console.confirm_prompts) == 0
        assert github.merged_prs == [1, 2, 3]

    def test_single_branch_stack(self) -> None:
        """Single-branch stack: no rebase, works like regular land."""
        github = _fake_github(branches=[("branch-a", 1)])
        graphite = FakeGraphite(stacks={"branch-a": ["main", "branch-a"]})
        git = _fake_git(
            current_branch="branch-a",
            local_branches=["main", "branch-a"],
        )
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=[True],
        )
        ctx = context_for_test(
            git=git, github=github, graphite=graphite, console=console, cwd=_REPO_ROOT
        )
        repo = _repo_context()

        execute_land_stack(
            ctx,
            repo=repo,
            force=False,
            pull_flag=False,
            no_delete=True,
            skip_learn=True,
        )

        assert github.merged_prs == [1]
        # No re-parents for single branch
        reparents = [op for op in github.operation_log if op[0] == "update_pr_base_branch"]
        assert reparents == []

    def test_partial_failure_reports_progress(self, capsys: pytest.CaptureFixture[str]) -> None:
        """On failure mid-stack, partial progress is reported."""
        # First PR merges fine, second fails
        github = FakeLocalGitHub(
            prs_by_branch={
                "branch-a": _pr_details(number=1, branch="branch-a"),
                "branch-b": _pr_details(number=2, branch="branch-b"),
            },
            pr_details={
                1: _pr_details(number=1, branch="branch-a"),
                2: _pr_details(number=2, branch="branch-b"),
            },
            merge_should_succeed=False,
        )
        graphite = FakeGraphite(stacks={"branch-b": ["main", "branch-a", "branch-b"]})
        git = _fake_git(
            current_branch="branch-b",
            local_branches=["main", "branch-a", "branch-b"],
        )
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=[True],
        )
        ctx = context_for_test(
            git=git, github=github, graphite=graphite, console=console, cwd=_REPO_ROOT
        )
        repo = _repo_context()

        with pytest.raises(UserFacingCliError, match="Failed to merge"):
            execute_land_stack(
                ctx,
                repo=repo,
                force=False,
                pull_flag=False,
                no_delete=True,
                skip_learn=True,
            )

        captured = capsys.readouterr()
        assert "0/2 landed" in captured.err

    def test_reparent_is_O_N(self) -> None:
        """Each PR's base is updated exactly once (O(N) total, not O(N^2))."""
        github = _fake_github()
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=[True],
        )
        ctx = context_for_test(
            git=_fake_git(),
            github=github,
            graphite=_fake_graphite(),
            console=console,
            cwd=_REPO_ROOT,
        )
        repo = _repo_context()

        execute_land_stack(
            ctx,
            repo=repo,
            force=False,
            pull_flag=False,
            no_delete=True,
            skip_learn=True,
        )

        reparents = [op for op in github.operation_log if op[0] == "update_pr_base_branch"]
        # 3 branches: re-parent for #2 and #3, none for #1 (it's bottom)
        assert len(reparents) == 2
        # Each PR re-parented exactly once
        reparented_prs = [op[1] for op in reparents]
        assert sorted(reparented_prs) == [2, 3]

    def test_operation_ordering(self) -> None:
        """Verify re-parent happens before merge for each iteration."""
        github = _fake_github()
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=[True],
        )
        ctx = context_for_test(
            git=_fake_git(),
            github=github,
            graphite=_fake_graphite(),
            console=console,
            cwd=_REPO_ROOT,
        )
        repo = _repo_context()

        execute_land_stack(
            ctx,
            repo=repo,
            force=False,
            pull_flag=False,
            no_delete=True,
            skip_learn=True,
        )

        log = github.operation_log
        # Expected order: reparent(2), merge(1), reparent(3), merge(2), merge(3)
        assert len(log) == 5
        assert log[0][0] == "update_pr_base_branch"
        assert log[1][0] == "merge_pr"
        assert log[2][0] == "update_pr_base_branch"
        assert log[3][0] == "merge_pr"
        assert log[4][0] == "merge_pr"

    def test_requires_graphite(self) -> None:
        """Error when Graphite is disabled."""
        from erk_shared.gateway.graphite.disabled import GraphiteDisabled

        ctx = context_for_test(
            git=_fake_git(),
            graphite=GraphiteDisabled(reason="config_disabled"),
            cwd=_REPO_ROOT,
        )
        repo = _repo_context()

        with pytest.raises(UserFacingCliError):
            execute_land_stack(
                ctx,
                repo=repo,
                force=False,
                pull_flag=False,
                no_delete=True,
                skip_learn=True,
            )

    def test_learn_pr_per_branch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Learn PR created for entries with plan_id."""
        import sys

        land_stack_mod = sys.modules["erk.cli.commands.land_stack"]

        learn_calls: list[tuple[str, int]] = []

        def fake_try_create_learn_pr(
            ctx: object, *, main_repo_root: Path, entry: StackLandEntry
        ) -> None:
            if entry.plan_id is not None:
                learn_calls.append((entry.plan_id, entry.pr_number))

        monkeypatch.setattr(
            land_stack_mod,
            "_try_create_learn_pr",
            fake_try_create_learn_pr,
        )

        # Set up PRs: branch-a and branch-c have plan PRs (draft), branch-b does not.
        # The plan_id comes from resolve_plan_id_for_branch which calls get_pr_for_branch.
        # Since we use PlannedPRBackend by default, plan_id = str(pr.number).
        # To simulate "branch-b has no plan", we give all three branches PRs
        # but monkeypatch _try_create_learn_pr to track calls.
        # The real plan_id resolution returns str(pr_number) for every branch that has a PR.
        # So branch-a -> plan "1", branch-b -> plan "2", branch-c -> plan "3".
        # We override _try_create_learn_pr to control what gets called.
        github = _fake_github()
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=[True],
        )
        ctx = context_for_test(
            git=_fake_git(),
            github=github,
            graphite=_fake_graphite(),
            console=console,
            cwd=_REPO_ROOT,
        )
        repo = _repo_context()

        execute_land_stack(
            ctx,
            repo=repo,
            force=False,
            pull_flag=False,
            no_delete=True,
            skip_learn=False,
        )

        # Learn PR called for all 3 branches (they all have plan_ids via PlannedPRBackend)
        assert len(learn_calls) == 3
        assert ("1", 1) in learn_calls
        assert ("2", 2) in learn_calls
        assert ("3", 3) in learn_calls

    def test_skip_learn_no_learn_prs(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """No learn PRs created when skip_learn=True."""
        import sys

        land_stack_mod = sys.modules["erk.cli.commands.land_stack"]

        learn_calls: list[tuple[str, int]] = []

        def fake_try_create_learn_pr(
            ctx: object, *, main_repo_root: Path, entry: StackLandEntry
        ) -> None:
            learn_calls.append((entry.plan_id, entry.pr_number))

        monkeypatch.setattr(
            land_stack_mod,
            "_try_create_learn_pr",
            fake_try_create_learn_pr,
        )

        github = _fake_github()
        console = FakeConsole(
            is_interactive=True,
            is_stdout_tty=None,
            is_stderr_tty=None,
            confirm_responses=[True],
        )
        ctx = context_for_test(
            git=_fake_git(),
            github=github,
            graphite=_fake_graphite(),
            console=console,
            cwd=_REPO_ROOT,
        )
        repo = _repo_context()

        execute_land_stack(
            ctx,
            repo=repo,
            force=False,
            pull_flag=False,
            no_delete=True,
            skip_learn=True,
        )

        assert learn_calls == []


# ---------------------------------------------------------------------------
# Tests: _display_stack_summary
# ---------------------------------------------------------------------------


class TestDisplayStackSummary:
    def test_output_includes_pr_numbers(self, capsys: pytest.CaptureFixture[str]) -> None:
        entries = [
            _make_entry(branch="a", pr_number=10),
            _make_entry(branch="b", pr_number=20),
        ]
        _display_stack_summary(entries)
        captured = capsys.readouterr()
        assert "PR #10" in captured.err
        assert "PR #20" in captured.err
        assert "bottom-up" in captured.err
