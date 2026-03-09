"""Tests for stack landing orchestration."""

from pathlib import Path

import pytest

from erk.cli.commands.land_stack import execute_land_stack
from erk.cli.ensure import UserFacingCliError
from erk.core.context import ErkContext, context_for_test
from erk.core.repo_discovery import RepoContext
from erk_shared.context.types import GlobalConfig
from erk_shared.fakes.git import FakeGit
from erk_shared.fakes.github import FakeLocalGitHub
from erk_shared.fakes.graphite import FakeGraphite
from erk_shared.gateway.git.abc import RebaseResult, WorktreeInfo
from erk_shared.gateway.github.types import PRDetails, PullRequestInfo
from erk_shared.gateway.graphite.types import BranchMetadata


def _make_pr_details(*, pr_number: int, branch: str, base_ref_name: str) -> PRDetails:
    return PRDetails(
        number=pr_number,
        url=f"https://github.com/owner/repo/pull/{pr_number}",
        title=f"PR for {branch}",
        body=f"Body for {branch}",
        state="OPEN",
        base_ref_name=base_ref_name,
        head_ref_name=branch,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        is_draft=False,
        is_cross_repository=False,
        owner="owner",
        repo="repo",
    )


def _make_pr_info(*, pr_number: int, branch: str) -> PullRequestInfo:
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


def _build_stack_context(
    tmp_path: Path,
    *,
    branches: tuple[str, ...],
    current_branch: str,
    worktree_branches: tuple[str, ...] | None = None,
    pr_base_update_should_apply: bool = True,
    rebase_onto_result: RebaseResult | None = None,
) -> tuple[RepoContext, FakeGit, FakeLocalGitHub, FakeGraphite, ErkContext]:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()

    erk_root = tmp_path / "erk-root"
    repo_dir = erk_root / "repos" / repo_root.name
    worktrees_dir = repo_dir / "worktrees"
    worktrees_dir.mkdir(parents=True)

    repo = RepoContext(
        root=repo_root,
        main_repo_root=repo_root,
        repo_name=repo_root.name,
        repo_dir=repo_dir,
        worktrees_dir=worktrees_dir,
        pool_json_path=repo_dir / "pool.json",
    )

    configured_worktree_branches = worktree_branches if worktree_branches is not None else branches
    worktree_paths: dict[str, Path] = {}
    worktree_infos = [WorktreeInfo(path=repo_root, branch="main", is_root=True)]
    current_branches = {repo_root: "main"}
    existing_paths = {repo_root, repo_root / ".git", repo_dir, worktrees_dir}
    git_common_dirs = {repo_root: repo_root / ".git"}
    repository_roots = {repo_root: repo_root}

    for branch in configured_worktree_branches:
        worktree_path = worktrees_dir / branch
        worktree_path.mkdir(parents=True)
        worktree_paths[branch] = worktree_path
        worktree_infos.append(WorktreeInfo(path=worktree_path, branch=branch, is_root=False))
        current_branches[worktree_path] = branch
        existing_paths.add(worktree_path)
        git_common_dirs[worktree_path] = repo_root / ".git"
        repository_roots[worktree_path] = repo_root

    cwd = worktree_paths[current_branch] if current_branch in worktree_paths else repo_root
    if cwd == repo_root:
        current_branches[repo_root] = current_branch
        worktree_infos[0] = WorktreeInfo(path=repo_root, branch=current_branch, is_root=True)

    local_branches = {repo_root: ["main", *branches]}
    fake_git = FakeGit(
        worktrees={repo_root: worktree_infos},
        current_branches=current_branches,
        local_branches=local_branches,
        trunk_branches={repo_root: "main"},
        git_common_dirs=git_common_dirs,
        repository_roots=repository_roots,
        existing_paths=existing_paths,
        rebase_onto_result=rebase_onto_result,
    )

    graphite_branches: dict[str, BranchMetadata] = {
        "main": BranchMetadata.trunk(
            "main",
            children=[branches[0]] if branches else [],
            commit_sha="main-sha",
        )
    }
    for index, branch in enumerate(branches):
        parent = "main" if index == 0 else branches[index - 1]
        children = [branches[index + 1]] if index + 1 < len(branches) else []
        graphite_branches[branch] = BranchMetadata.branch(
            branch,
            parent,
            children=children,
            commit_sha=f"{branch}-sha",
        )
    fake_graphite = FakeGraphite(branches=graphite_branches)

    pr_details: dict[int, PRDetails] = {}
    prs: dict[str, PullRequestInfo] = {}
    prs_by_branch: dict[str, PRDetails] = {}
    pr_bases: dict[int, str] = {}
    for offset, branch in enumerate(branches):
        pr_number = 101 + offset
        base_branch = "main" if offset == 0 else branches[offset - 1]
        details = _make_pr_details(pr_number=pr_number, branch=branch, base_ref_name=base_branch)
        pr_details[pr_number] = details
        prs[branch] = _make_pr_info(pr_number=pr_number, branch=branch)
        prs_by_branch[branch] = details
        pr_bases[pr_number] = base_branch

    fake_github = FakeLocalGitHub(
        prs=prs,
        pr_details=pr_details,
        prs_by_branch=prs_by_branch,
        pr_bases=pr_bases,
        pr_base_update_should_apply=pr_base_update_should_apply,
    )

    test_ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        graphite=fake_graphite,
        cwd=cwd,
        repo=repo,
        global_config=GlobalConfig.test(erk_root=erk_root, use_graphite=True),
    )
    return repo, fake_git, fake_github, fake_graphite, test_ctx


def test_execute_land_stack_merges_full_stack_bottom_up(tmp_path: Path) -> None:
    """Stack landing rebases and merges each branch from trunk upward."""
    repo, fake_git, fake_github, fake_graphite, ctx = _build_stack_context(
        tmp_path,
        branches=("feature-a", "feature-b", "feature-c"),
        current_branch="feature-c",
    )

    with pytest.raises(SystemExit) as exc:
        execute_land_stack(
            ctx,
            repo=repo,
            script=False,
            force=True,
            pull_flag=False,
            no_delete=True,
            skip_learn=True,
        )

    assert exc.value.code == 0
    assert fake_github.merged_prs == [101, 102, 103]
    assert fake_github.updated_pr_bases == [(102, "main"), (103, "main")]
    assert fake_graphite.track_branch_calls == [
        (repo.root, "feature-b", "main"),
        (repo.root, "feature-c", "main"),
    ]
    assert fake_graphite.retrack_branch_calls == [
        (repo.root, "feature-b"),
        (repo.root, "feature-c"),
    ]
    assert fake_git.rebase_onto_calls == [
        (repo.worktrees_dir / "feature-b", "origin/main"),
        (repo.worktrees_dir / "feature-c", "origin/main"),
    ]
    assert [push.branch for push in fake_git.pushed_branches] == ["feature-b", "feature-c"]


def test_execute_land_stack_aborts_before_merge_when_pr_reparenting_is_not_applied(
    tmp_path: Path,
) -> None:
    """Stack landing fails closed when GitHub base updates do not stick."""
    repo, _fake_git, fake_github, _fake_graphite, ctx = _build_stack_context(
        tmp_path,
        branches=("feature-a", "feature-b", "feature-c"),
        current_branch="feature-c",
        pr_base_update_should_apply=False,
    )

    with pytest.raises(UserFacingCliError) as exc:
        execute_land_stack(
            ctx,
            repo=repo,
            script=False,
            force=True,
            pull_flag=False,
            no_delete=True,
            skip_learn=True,
        )

    assert "Failed to update child PR #102" in exc.value.message
    assert fake_github.merged_prs == []


def test_execute_land_stack_reuses_cleanup_paths_after_full_success(tmp_path: Path) -> None:
    """Successful stack landing reuses existing cleanup code for local deletion."""
    repo, fake_git, fake_github, fake_graphite, ctx = _build_stack_context(
        tmp_path,
        branches=("feature-a",),
        current_branch="feature-a",
    )

    with pytest.raises(SystemExit) as exc:
        execute_land_stack(
            ctx,
            repo=repo,
            script=False,
            force=True,
            pull_flag=False,
            no_delete=False,
            skip_learn=True,
        )

    assert exc.value.code == 0
    assert fake_github.merged_prs == [101]
    assert fake_graphite.delete_branch_calls == [(repo.root, "feature-a")]
    assert fake_git.removed_worktrees == [repo.worktrees_dir / "feature-a"]


def test_execute_land_stack_reports_partial_progress_after_rebase_conflict(tmp_path: Path) -> None:
    """A rebase conflict preserves prior merges and aborts with retry guidance."""
    repo, fake_git, fake_github, _fake_graphite, ctx = _build_stack_context(
        tmp_path,
        branches=("feature-a", "feature-b", "feature-c"),
        current_branch="feature-c",
        rebase_onto_result=RebaseResult(success=False, conflict_files=("conflict.py",)),
    )

    with pytest.raises(UserFacingCliError) as exc:
        execute_land_stack(
            ctx,
            repo=repo,
            script=False,
            force=True,
            pull_flag=False,
            no_delete=True,
            skip_learn=True,
        )

    assert "Merged so far:\n  - PR #101 [feature-a]" in exc.value.message
    assert "Then retry: erk land --stack" in exc.value.message
    assert fake_github.merged_prs == [101]
    assert fake_git.rebase_abort_calls == [repo.worktrees_dir / "feature-b"]
