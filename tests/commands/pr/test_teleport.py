"""Tests for erk pr teleport command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.pr import pr_group
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state, save_pool_state
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.graphite.types import BranchMetadata
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.fakes.gateway.graphite import FakeGraphite
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env


def _make_pr_details(
    number: int,
    head_ref_name: str,
    *,
    is_cross_repository: bool = False,
    state: str = "OPEN",
    base_ref_name: str = "main",
) -> PRDetails:
    return PRDetails(
        number=number,
        url=f"https://github.com/owner/repo/pull/{number}",
        title=f"PR #{number}",
        body="",
        state=state,
        is_draft=False,
        base_ref_name=base_ref_name,
        head_ref_name=head_ref_name,
        is_cross_repository=is_cross_repository,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="owner",
        repo="repo",
    )


def test_teleport_pr_not_found() -> None:
    """Teleport errors when PR doesn't exist."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        github = FakeLocalGitHub(pr_details={})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "999"], obj=ctx)
        assert result.exit_code == 1
        assert "Could not find PR #999" in result.output


def test_teleport_cross_repo_errors() -> None:
    """Teleport rejects cross-repository (fork) PRs."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        pr = _make_pr_details(123, "feature", is_cross_repository=True)
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "123"], obj=ctx)
        assert result.exit_code == 1
        assert "cross-repository" in result.output


def test_teleport_wrong_branch_switches_and_teleports() -> None:
    """Teleport automatically switches branch when it's not yet checked out."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        pr = _make_pr_details(123, "feature-branch")
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},  # feature-branch doesn't exist yet
            remote_branches={env.cwd: ["origin/main", "origin/feature-branch"]},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "123", "--force"], obj=ctx)
        assert result.exit_code == 0
        assert "Teleported" in result.output
        assert "feature-branch" in result.output


def test_teleport_wrong_branch_exists_in_other_worktree() -> None:
    """Teleport prints activation instructions when branch is already checked out elsewhere."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        other_worktree_path = env.repo.worktrees_dir / "other"
        pr = _make_pr_details(123, "feature-branch")
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=other_worktree_path, branch="feature-branch", is_root=False),
                ]
            },
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "123"], obj=ctx)
        assert result.exit_code == 0
        assert "feature-branch" in result.output
        assert str(other_worktree_path) in result.output


def test_teleport_in_place_with_force() -> None:
    """Teleport force-resets current branch to match remote."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        pr = _make_pr_details(123, "feature-branch")
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            local_branches={env.cwd: ["main", "feature-branch"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-branch"]},
            ahead_behind={(env.cwd, "feature-branch"): (1, 2)},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "123", "--force"], obj=ctx)
        assert result.exit_code == 0
        assert "Teleported" in result.output
        assert "feature-branch" in result.output


def test_teleport_already_in_sync_exits_cleanly() -> None:
    """Teleport exits with 0 when branch is already in sync."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        pr = _make_pr_details(123, "feature-branch")
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            local_branches={env.cwd: ["main", "feature-branch"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-branch"]},
            ahead_behind={(env.cwd, "feature-branch"): (0, 0)},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "123"], obj=ctx)
        assert result.exit_code == 0
        assert "already in sync" in result.output


def test_teleport_stacked_pr_fetches_base_with_graphite() -> None:
    """Teleport fetches base branch and tracks with Graphite for stacked PRs."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        # Stacked PR: base is not main
        pr = _make_pr_details(
            123,
            "plnd/add-print-statement",
            base_ref_name="plnd/rename-sync-teleport",
        )
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},  # Base branch not yet local
            remote_branches={
                env.cwd: [
                    "origin/main",
                    "origin/plnd/rename-sync-teleport",
                    "origin/plnd/add-print-statement",
                ]
            },
        )
        graphite = FakeGraphite(
            branches={
                "plnd/rename-sync-teleport": BranchMetadata(
                    name="plnd/rename-sync-teleport",
                    parent="main",
                    children=["plnd/add-print-statement"],
                    is_trunk=False,
                    commit_sha=None,
                ),
            }
        )
        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, use_graphite=True
        )
        result = runner.invoke(pr_group, ["teleport", "123", "--force"], obj=ctx)
        assert result.exit_code == 0
        assert "Fetching base branch" in result.output
        assert "Tracking branch with Graphite" in result.output
        # Verify base branch was fetched
        assert ("origin", "plnd/rename-sync-teleport") in git.fetched_branches
        # Verify tracking branch was created for base
        assert (
            "plnd/rename-sync-teleport",
            "origin/plnd/rename-sync-teleport",
        ) in git.created_tracking_branches


def test_teleport_trunk_parent_tracks_without_base_fetch() -> None:
    """Teleport skips base fetch but still tracks with Graphite for non-stacked PRs."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        # PR with base = main (trunk) — not stacked, but still needs Graphite tracking
        pr = _make_pr_details(123, "feature-branch", base_ref_name="main")
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-branch"]},
        )
        graphite = FakeGraphite()
        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, use_graphite=True
        )
        result = runner.invoke(pr_group, ["teleport", "123", "--force"], obj=ctx)
        assert result.exit_code == 0
        assert "Fetching base branch" not in result.output
        assert "Tracking branch with Graphite" in result.output
        # No base branch fetching (trunk is already local)
        assert len(git.created_tracking_branches) == 0


def test_teleport_already_tracked_retracks() -> None:
    """Teleport retracks already-tracked branches after force-reset."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        # Stacked PR
        pr = _make_pr_details(
            123,
            "plnd/add-print-statement",
            base_ref_name="plnd/rename-sync-teleport",
        )
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            local_branches={
                env.cwd: [
                    "main",
                    "plnd/rename-sync-teleport",
                    "plnd/add-print-statement",
                ]
            },
            remote_branches={
                env.cwd: [
                    "origin/main",
                    "origin/plnd/rename-sync-teleport",
                    "origin/plnd/add-print-statement",
                ]
            },
            ahead_behind={(env.cwd, "plnd/add-print-statement"): (2, 0)},
        )
        # Configure branch as already tracked by Graphite
        graphite = FakeGraphite(
            branches={
                "plnd/rename-sync-teleport": BranchMetadata(
                    name="plnd/rename-sync-teleport",
                    parent="main",
                    children=["plnd/add-print-statement"],
                    is_trunk=False,
                    commit_sha=None,
                ),
                "plnd/add-print-statement": BranchMetadata(
                    name="plnd/add-print-statement",
                    parent="plnd/rename-sync-teleport",
                    children=[],
                    is_trunk=False,
                    commit_sha=None,
                ),
            }
        )
        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, use_graphite=True
        )
        result = runner.invoke(pr_group, ["teleport", "123", "--force"], obj=ctx)
        assert result.exit_code == 0
        assert "Tracking branch with Graphite" not in result.output  # Already tracked
        # Verify retrack was called - check git's tracked branches
        # (should be empty since graphite_branch_ops.retrack was called)
        # The retrack happens via graphite_branch_ops, so we just verify no fresh track happened
        assert len(git.created_tracking_branches) == 0  # Fresh tracking not called


def test_teleport_new_slot_existing_worktree_navigates() -> None:
    """Teleport --new-slot navigates to existing worktree instead of erroring."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        other_worktree_path = env.repo.worktrees_dir / "other"
        pr = _make_pr_details(300, "feature-existing")
        github = FakeLocalGitHub(pr_details={300: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(
                        path=other_worktree_path, branch="feature-existing", is_root=False
                    ),
                ]
            },
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "300", "--new-slot"], obj=ctx)
        assert result.exit_code == 0
        assert "feature-existing" in result.output
        assert str(other_worktree_path) in result.output


def test_teleport_new_slot_existing_worktree_script_mode() -> None:
    """Teleport --new-slot --script navigates to existing worktree with valid script."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        other_worktree_path = env.repo.worktrees_dir / "other"
        pr = _make_pr_details(301, "feature-existing-script")
        github = FakeLocalGitHub(pr_details={301: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(
                        path=other_worktree_path,
                        branch="feature-existing-script",
                        is_root=False,
                    ),
                ]
            },
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "301", "--new-slot", "--script"], obj=ctx)
        assert result.exit_code == 0
        script_path_str = result.stdout.strip()
        assert script_path_str != ""
        script_content = Path(script_path_str).read_text(encoding="utf-8")
        assert str(other_worktree_path) in script_content
        assert "gt submit --no-interactive" not in script_content


def test_teleport_new_slot_script_mode_with_sync_includes_gt_submit() -> None:
    """Test teleport --new-slot --script --sync includes gt submit in activation script.

    When teleporting into a new slot with --script and --sync, the activation
    script should contain 'gt submit --no-interactive' as a post-cd command.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        pr = _make_pr_details(200, "feature-sync")
        github = FakeLocalGitHub(pr_details={200: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-sync"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-sync"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github, use_graphite=True)

        result = runner.invoke(
            pr_group, ["teleport", "200", "--new-slot", "--script", "--sync"], obj=ctx
        )

        assert result.exit_code == 0
        script_path_str = result.stdout.strip()
        assert script_path_str != ""
        script_content = Path(script_path_str).read_text(encoding="utf-8")
        assert "gt submit --no-interactive" in script_content


def test_teleport_new_slot_script_mode_without_sync_omits_gt_submit() -> None:
    """Test teleport --new-slot --script without --sync omits gt submit.

    When --sync is not passed, the activation script should not include
    gt submit even in script mode.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        pr = _make_pr_details(201, "feature-no-sync")
        github = FakeLocalGitHub(pr_details={201: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-no-sync"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-no-sync"]},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github, use_graphite=True)

        result = runner.invoke(pr_group, ["teleport", "201", "--new-slot", "--script"], obj=ctx)

        assert result.exit_code == 0
        script_path_str = result.stdout.strip()
        assert script_path_str != ""
        script_content = Path(script_path_str).read_text(encoding="utf-8")
        assert "gt submit --no-interactive" not in script_content


def test_teleport_in_place_script_mode_with_sync_includes_gt_submit() -> None:
    """Test teleport --script --sync in-place includes gt submit in activation script."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        env.setup_repo_structure()
        pr = _make_pr_details(202, "feature-in-place")
        github = FakeLocalGitHub(pr_details={202: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-in-place"},
            trunk_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-in-place"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-in-place"]},
            ahead_behind={(env.cwd, "feature-in-place"): (0, 1)},
            existing_paths={env.cwd, env.repo.worktrees_dir},
        )
        ctx = build_workspace_test_context(env, git=git, github=github, use_graphite=True)

        result = runner.invoke(
            pr_group, ["teleport", "202", "--force", "--script", "--sync"], obj=ctx
        )

        assert result.exit_code == 0
        script_path_str = result.stdout.strip()
        assert script_path_str != ""
        script_content = Path(script_path_str).read_text(encoding="utf-8")
        assert "gt submit --no-interactive" in script_content


def test_teleport_in_place_updates_slot_assignment() -> None:
    """Teleport in a slot-assigned worktree updates the slot assignment to the new branch."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        pr = _make_pr_details(500, "new-feature-branch")
        github = FakeLocalGitHub(pr_details={500: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "old-branch"},
            local_branches={env.cwd: ["main", "old-branch"]},
            remote_branches={env.cwd: ["origin/main", "origin/new-feature-branch"]},
            repository_roots={env.cwd: env.cwd},
        )

        # Write initial pool state with a slot assigned to old-branch at env.cwd
        initial_state = PoolState(
            version="1.0",
            pool_size=4,
            slots=(),
            assignments=(
                SlotAssignment(
                    slot_name="erk-slot-01",
                    branch_name="old-branch",
                    assigned_at="2026-01-01T00:00:00",
                    worktree_path=env.cwd,
                ),
            ),
        )
        save_pool_state(env.repo.pool_json_path, initial_state)

        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "500", "--force"], obj=ctx)
        assert result.exit_code == 0
        assert "Teleported" in result.output
        assert "new-feature-branch" in result.output

        # Verify slot assignment was updated to the new branch
        updated_state = load_pool_state(env.repo.pool_json_path)
        assert updated_state is not None
        assert len(updated_state.assignments) == 1
        assignment = updated_state.assignments[0]
        assert assignment.slot_name == "erk-slot-01"
        assert assignment.branch_name == "new-feature-branch"
        assert assignment.worktree_path == env.cwd


def test_teleport_dry_run_in_place_shows_local_state() -> None:
    """Dry run shows local commits, staged/modified files, and operations."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        pr = _make_pr_details(123, "feature-branch")
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            local_branches={env.cwd: ["main", "feature-branch"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-branch"]},
            ahead_behind={(env.cwd, "feature-branch"): (2, 1)},
            file_statuses={env.cwd: (["src/foo.py", "src/bar.py"], ["src/baz.py"], ["tmp.txt"])},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "123", "--dry-run"], obj=ctx)
        assert result.exit_code == 0
        assert "Dry run: erk pr teleport 123" in result.output
        assert "2 local commit(s) ahead of remote (would be lost)" in result.output
        assert "2 staged file(s): src/foo.py, src/bar.py" in result.output
        assert "1 modified file(s): src/baz.py" in result.output
        assert "1 untracked file(s)" in result.output
        assert "Would force-reset" in result.output
        assert "[DRY RUN] No changes made" in result.output


def test_teleport_dry_run_in_place_already_in_sync() -> None:
    """Dry run still shows 'already in sync' when branch matches remote."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        pr = _make_pr_details(123, "feature-branch")
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            local_branches={env.cwd: ["main", "feature-branch"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-branch"]},
            ahead_behind={(env.cwd, "feature-branch"): (0, 0)},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "123", "--dry-run"], obj=ctx)
        assert result.exit_code == 0
        assert "already in sync" in result.output


def test_teleport_dry_run_no_mutations() -> None:
    """Dry run does not perform any git mutations."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        pr = _make_pr_details(123, "feature-branch")
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            local_branches={env.cwd: ["main", "feature-branch"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-branch"]},
            ahead_behind={(env.cwd, "feature-branch"): (3, 0)},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "123", "--dry-run"], obj=ctx)
        assert result.exit_code == 0
        # Verify no mutations occurred
        assert len(git.created_branches) == 0
        assert len(git.checked_out_branches) == 0


def test_teleport_dry_run_new_slot() -> None:
    """Dry run with --new-slot shows 'Would create new worktree slot'."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        pr = _make_pr_details(123, "feature-branch")
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-branch"]},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "123", "--new-slot", "--dry-run"], obj=ctx)
        assert result.exit_code == 0
        assert "Would create new worktree slot" in result.output
        assert "[DRY RUN] No changes made" in result.output


def test_teleport_dry_run_with_sync() -> None:
    """Dry run with --sync shows 'Would run gt submit'."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        pr = _make_pr_details(123, "feature-branch")
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
            local_branches={env.cwd: ["main", "feature-branch"]},
            remote_branches={env.cwd: ["origin/main", "origin/feature-branch"]},
            ahead_behind={(env.cwd, "feature-branch"): (1, 0)},
        )
        ctx = build_workspace_test_context(env, git=git, github=github)
        result = runner.invoke(pr_group, ["teleport", "123", "--dry-run", "--sync"], obj=ctx)
        assert result.exit_code == 0
        assert "Would run gt submit --no-interactive" in result.output


def test_teleport_dry_run_with_graphite() -> None:
    """Dry run with Graphite enabled shows tracking operations."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner, env_overrides=None) as env:
        pr = _make_pr_details(
            123,
            "plnd/add-feature",
            base_ref_name="plnd/parent-branch",
        )
        github = FakeLocalGitHub(pr_details={123: pr})
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "plnd/add-feature"},
            local_branches={env.cwd: ["main", "plnd/add-feature"]},
            remote_branches={
                env.cwd: [
                    "origin/main",
                    "origin/plnd/parent-branch",
                    "origin/plnd/add-feature",
                ]
            },
            ahead_behind={(env.cwd, "plnd/add-feature"): (1, 0)},
        )
        graphite = FakeGraphite()
        ctx = build_workspace_test_context(
            env, git=git, github=github, graphite=graphite, use_graphite=True
        )
        result = runner.invoke(pr_group, ["teleport", "123", "--dry-run"], obj=ctx)
        assert result.exit_code == 0
        assert "Would fetch base branch 'plnd/parent-branch'" in result.output
        assert "Would track branch with Graphite (base: plnd/parent-branch)" in result.output
        # Verify no actual Graphite operations occurred
        assert len(git.created_tracking_branches) == 0
